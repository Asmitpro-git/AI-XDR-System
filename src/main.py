import json
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session

from src.database import get_session, init_db
from src.models import Alert, IOC, ResponseAction
from src.schemas import (
    AlertRead,
    AlertStatus,
    AlertStatusUpdate,
    DashboardSummaryRead,
    EventCreate,
    EventIngestResponse,
    EventRead,
    IOCCreate,
    IOCRead,
    ResponseActionCreate,
    ResponseActionRead,
)
from src.services.xdr import ConflictError, NotFoundError, ValidationError, XDRService

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="XDR MVP API",
    version="0.1.0",
    description="A practical starter for telemetry ingestion, detection, and response workflows.",
    lifespan=lifespan,
)
app.mount("/static", StaticFiles(directory=STATIC_DIR, check_dir=False), name="static")

SessionDep = Annotated[Session, Depends(get_session)]
xdr_service = XDRService()


@app.get("/")
def root() -> dict[str, str]:
    return {
        "name": "xdr-mvp",
        "status": "ready",
        "docs": "/docs",
        "dashboard": "/dashboard",
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/dashboard", include_in_schema=False)
def dashboard() -> FileResponse:
    return FileResponse(STATIC_DIR / "dashboard.html")


@app.get("/view/alerts", include_in_schema=False)
def alerts_page() -> FileResponse:
    return FileResponse(STATIC_DIR / "alerts.html")


@app.get("/view/iocs", include_in_schema=False)
def iocs_page() -> FileResponse:
    return FileResponse(STATIC_DIR / "iocs.html")


@app.get("/view/reports", include_in_schema=False)
def reports_page() -> FileResponse:
    return FileResponse(STATIC_DIR / "reports.html")


@app.post("/iocs", response_model=IOCRead, status_code=201)
def create_ioc(payload: IOCCreate, session: SessionDep) -> IOC:
    try:
        return xdr_service.create_ioc(payload, session)
    except ConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.get("/iocs", response_model=list[IOCRead])
def list_iocs(session: SessionDep) -> list[IOC]:
    return xdr_service.list_iocs(session)


@app.post("/events", response_model=EventIngestResponse, status_code=201)
def ingest_event(payload: EventCreate, session: SessionDep) -> EventIngestResponse:
    event, alerts = xdr_service.ingest_event(payload, session)

    return EventIngestResponse(
        event_id=event.id or 0,
        alert_ids=[alert.id for alert in alerts if alert.id is not None],
        message=f"Event ingested. Generated {len(alerts)} alert(s).",
    )


@app.get("/events", response_model=list[EventRead])
def list_events(
    session: SessionDep,
    limit: int = Query(default=100, ge=1, le=500),
) -> list[EventRead]:
    events = xdr_service.list_events(session, limit)
    return [
        EventRead(
            id=event.id or 0,
            timestamp=event.timestamp,
            source=event.source,
            host=event.host,
            user=event.user,
            source_ip=event.source_ip,
            event_type=event.event_type,
            severity=event.severity,
            details=_parse_event_details(event.details),
            raw_message=event.raw_message,
        )
        for event in events
    ]


@app.get("/dashboard/summary", response_model=DashboardSummaryRead)
def dashboard_summary(session: SessionDep) -> DashboardSummaryRead:
    return DashboardSummaryRead.model_validate(xdr_service.dashboard_summary(session))


@app.get("/alerts", response_model=list[AlertRead])
def list_alerts(
    session: SessionDep,
    status: AlertStatus | None = Query(default=None),
) -> list[Alert]:
    return xdr_service.list_alerts(session, status)


@app.patch("/alerts/{alert_id}", response_model=AlertRead)
def update_alert_status(
    alert_id: int,
    payload: AlertStatusUpdate,
    session: SessionDep,
) -> Alert:
    try:
        return xdr_service.update_alert_status(alert_id, payload.status, session)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/alerts/{alert_id}/respond", response_model=ResponseActionRead, status_code=201)
def queue_alert_response(
    alert_id: int,
    payload: ResponseActionCreate,
    session: SessionDep,
) -> ResponseAction:
    try:
        return xdr_service.queue_response(alert_id, payload, session)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/responses", response_model=list[ResponseActionRead])
def list_responses(session: SessionDep) -> list[ResponseAction]:
    return xdr_service.list_responses(session)


def _parse_event_details(raw_details: str) -> dict[str, object]:
    try:
        parsed = json.loads(raw_details)
    except (TypeError, json.JSONDecodeError):
        return {}
    if isinstance(parsed, dict):
        return parsed
    return {}

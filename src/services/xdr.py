import json
from collections import Counter

from sqlmodel import Session, select

from src.models import Alert, IOC, ResponseAction, TelemetryEvent, utc_now
from src.schemas import AlertStatus, EventCreate, IOCCreate, ResponseActionCreate
from src.services.detection import DetectionEngine, build_default_engine
from src.services.response import ALLOWED_ACTIONS, queue_response_action


class ServiceError(Exception):
    """Base exception for XDR service errors."""


class ConflictError(ServiceError):
    """Raised when a write request conflicts with existing state."""


class NotFoundError(ServiceError):
    """Raised when an entity cannot be found."""


class ValidationError(ServiceError):
    """Raised when service-level validation fails."""


class XDRService:
    def __init__(self, detection_engine: DetectionEngine | None = None) -> None:
        self._detection_engine = detection_engine or build_default_engine()

    def create_ioc(self, payload: IOCCreate, session: Session) -> IOC:
        normalized_value = payload.value.strip().lower()
        existing = session.exec(select(IOC).where(IOC.value == normalized_value)).first()
        if existing:
            raise ConflictError("IOC already exists")

        ioc = IOC(
            ioc_type=payload.ioc_type.strip().lower(),
            value=normalized_value,
            confidence=payload.confidence,
        )
        session.add(ioc)
        session.commit()
        session.refresh(ioc)
        return ioc

    def list_iocs(self, session: Session) -> list[IOC]:
        statement = select(IOC).order_by(IOC.created_at.desc())
        return session.exec(statement).all()

    def list_events(self, session: Session, limit: int = 100) -> list[TelemetryEvent]:
        statement = select(TelemetryEvent).order_by(TelemetryEvent.timestamp.desc()).limit(limit)
        return session.exec(statement).all()

    def ingest_event(
        self,
        payload: EventCreate,
        session: Session,
    ) -> tuple[TelemetryEvent, list[Alert]]:
        event = TelemetryEvent(
            timestamp=payload.timestamp or utc_now(),
            source=payload.source.strip().lower(),
            host=payload.host.strip(),
            user=payload.user.strip() if payload.user else None,
            source_ip=payload.source_ip.strip() if payload.source_ip else None,
            event_type=payload.event_type.strip().lower(),
            severity=payload.severity.lower(),
            details=json.dumps(payload.details, ensure_ascii=True, sort_keys=True),
            raw_message=payload.raw_message,
        )
        session.add(event)
        session.commit()
        session.refresh(event)

        alerts = self._detection_engine.evaluate(session, event)
        if alerts:
            session.commit()
            for alert in alerts:
                session.refresh(alert)
        return event, alerts

    def list_alerts(self, session: Session, status: AlertStatus | None = None) -> list[Alert]:
        statement = select(Alert)
        if status:
            statement = statement.where(Alert.status == status)
        statement = statement.order_by(Alert.created_at.desc())
        return session.exec(statement).all()

    def update_alert_status(self, alert_id: int, status: AlertStatus, session: Session) -> Alert:
        alert = session.get(Alert, alert_id)
        if not alert:
            raise NotFoundError("Alert not found")

        alert.status = status
        session.add(alert)
        session.commit()
        session.refresh(alert)
        return alert

    def queue_response(
        self,
        alert_id: int,
        payload: ResponseActionCreate,
        session: Session,
    ) -> ResponseAction:
        if payload.action_type not in ALLOWED_ACTIONS:
            raise ValidationError("Unsupported action type")

        alert = session.get(Alert, alert_id)
        if not alert:
            raise NotFoundError("Alert not found")

        try:
            action = queue_response_action(alert, payload.action_type, payload.notes)
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc

        session.add(alert)
        session.add(action)
        session.commit()
        session.refresh(action)
        return action

    def list_responses(self, session: Session) -> list[ResponseAction]:
        statement = select(ResponseAction).order_by(ResponseAction.requested_at.desc())
        return session.exec(statement).all()

    def dashboard_summary(self, session: Session) -> dict[str, int | dict[str, int]]:
        events = session.exec(select(TelemetryEvent)).all()
        iocs = session.exec(select(IOC)).all()
        alerts = session.exec(select(Alert)).all()
        responses = session.exec(select(ResponseAction)).all()

        status_counts = Counter(alert.status for alert in alerts)
        severity_counts = Counter(alert.severity for alert in alerts)
        source_counts = Counter(event.source for event in events)
        response_counts = Counter(response.status for response in responses)

        return {
            "total_events": len(events),
            "total_iocs": len(iocs),
            "total_alerts": len(alerts),
            "open_alerts": status_counts.get("open", 0),
            "investigating_alerts": status_counts.get("investigating", 0),
            "resolved_alerts": status_counts.get("resolved", 0),
            "false_positive_alerts": status_counts.get("false_positive", 0),
            "queued_responses": response_counts.get("queued", 0),
            "executed_responses": response_counts.get("executed", 0),
            "alerts_by_severity": dict(sorted(severity_counts.items())),
            "events_by_source": dict(sorted(source_counts.items())),
        }
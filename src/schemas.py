from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

Severity = Literal["low", "medium", "high", "critical"]
AlertStatus = Literal["open", "investigating", "resolved", "false_positive"]
ActionType = Literal[
    "isolate_host",
    "block_ip",
    "disable_user",
    "collect_forensics",
]


class EventCreate(BaseModel):
    source: str = Field(min_length=2, max_length=32)
    host: str = Field(min_length=1, max_length=128)
    user: str | None = Field(default=None, max_length=128)
    source_ip: str | None = Field(default=None, max_length=64)
    event_type: str = Field(min_length=2, max_length=64)
    severity: Severity = "low"
    details: dict[str, Any] = Field(default_factory=dict)
    raw_message: str | None = Field(default=None, max_length=4000)
    timestamp: datetime | None = None


class EventIngestResponse(BaseModel):
    event_id: int
    alert_ids: list[int]
    message: str


class EventRead(BaseModel):
    id: int
    timestamp: datetime
    source: str
    host: str
    user: str | None
    source_ip: str | None
    event_type: str
    severity: str
    details: dict[str, Any]
    raw_message: str | None


class IOCCreate(BaseModel):
    ioc_type: str = Field(min_length=2, max_length=32)
    value: str = Field(min_length=3, max_length=512)
    confidence: int = Field(default=50, ge=1, le=100)


class IOCRead(BaseModel):
    id: int
    created_at: datetime
    ioc_type: str
    value: str
    confidence: int


class AlertRead(BaseModel):
    id: int
    created_at: datetime
    title: str
    description: str
    severity: str
    status: str
    rule_name: str
    entity: str
    event_id: int | None


class AlertStatusUpdate(BaseModel):
    status: AlertStatus


class ResponseActionCreate(BaseModel):
    action_type: ActionType
    notes: str | None = Field(default=None, max_length=2000)


class ResponseActionRead(BaseModel):
    id: int
    alert_id: int
    action_type: str
    status: str
    notes: str | None
    requested_at: datetime
    executed_at: datetime | None


class DashboardSummaryRead(BaseModel):
    total_events: int
    total_iocs: int
    total_alerts: int
    open_alerts: int
    investigating_alerts: int
    resolved_alerts: int
    false_positive_alerts: int
    queued_responses: int
    executed_responses: int
    alerts_by_severity: dict[str, int]
    events_by_source: dict[str, int]

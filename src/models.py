from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class TelemetryEvent(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    timestamp: datetime = Field(default_factory=utc_now, index=True)
    source: str = Field(index=True, max_length=32)
    host: str = Field(index=True, max_length=128)
    user: Optional[str] = Field(default=None, index=True, max_length=128)
    source_ip: Optional[str] = Field(default=None, index=True, max_length=64)
    event_type: str = Field(index=True, max_length=64)
    severity: str = Field(default="low", max_length=16)
    details: str = Field(default="{}", max_length=4000)
    raw_message: Optional[str] = Field(default=None, max_length=4000)


class IOC(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=utc_now, index=True)
    ioc_type: str = Field(max_length=32)
    value: str = Field(unique=True, index=True, max_length=512)
    confidence: int = Field(default=50, ge=1, le=100)


class Alert(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=utc_now, index=True)
    title: str = Field(max_length=200)
    description: str = Field(max_length=2000)
    severity: str = Field(default="medium", max_length=16)
    status: str = Field(default="open", index=True, max_length=32)
    rule_name: str = Field(index=True, max_length=64)
    entity: str = Field(max_length=128)
    event_id: Optional[int] = Field(default=None, index=True)


class ResponseAction(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    alert_id: int = Field(index=True)
    action_type: str = Field(max_length=64)
    status: str = Field(default="queued", max_length=32)
    notes: Optional[str] = Field(default=None, max_length=2000)
    requested_at: datetime = Field(default_factory=utc_now, index=True)
    executed_at: Optional[datetime] = Field(default=None)

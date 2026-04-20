import json
from dataclasses import dataclass
from datetime import timedelta
from typing import Protocol, Sequence

from sqlmodel import Session, select

from src.models import Alert, IOC, TelemetryEvent

SUSPICIOUS_PROCESS_HINTS = (
    "powershell -enc",
    "mimikatz",
    "rundll32",
    "certutil -urlcache",
    "wmic process call create",
)


@dataclass(frozen=True)
class DetectionContext:
    session: Session
    event: TelemetryEvent
    searchable_text: str
    details: dict[str, object]


class DetectionRule(Protocol):
    rule_name: str

    def run(self, context: DetectionContext) -> list[Alert]:
        ...


class IOCMatchRule:
    rule_name = "ioc_match"

    def run(self, context: DetectionContext) -> list[Alert]:
        iocs = context.session.exec(select(IOC)).all()
        if not iocs:
            return []

        alerts = []
        for ioc in iocs:
            ioc_value = ioc.value.strip().lower()
            if not ioc_value:
                continue
            if ioc_value in context.searchable_text:
                alerts.append(
                    Alert(
                        title=f"IOC match detected: {ioc.value}",
                        description=(
                            "Event matched a known IOC. Validate source context and "
                            "scope possible lateral movement."
                        ),
                        severity=_severity_from_confidence(ioc.confidence),
                        rule_name=self.rule_name,
                        entity=context.event.host,
                        event_id=context.event.id,
                    )
                )
        return alerts


class AuthBruteforceRule:
    rule_name = "auth_bruteforce"

    def run(self, context: DetectionContext) -> list[Alert]:
        event = context.event
        if event.event_type != "auth_failed" or not event.source_ip:
            return []

        window_start = event.timestamp - timedelta(minutes=5)
        statement = select(TelemetryEvent).where(
            TelemetryEvent.event_type == "auth_failed",
            TelemetryEvent.source_ip == event.source_ip,
            TelemetryEvent.timestamp >= window_start,
        )
        failed_attempts = context.session.exec(statement).all()
        if len(failed_attempts) < 5:
            return []

        return [
            Alert(
                title="Possible brute-force authentication attack",
                description=(
                    f"Detected {len(failed_attempts)} failed authentication events "
                    f"from {event.source_ip} in the last 5 minutes."
                ),
                severity="high",
                rule_name=self.rule_name,
                entity=event.source_ip,
                event_id=event.id,
            )
        ]


class SuspiciousProcessRule:
    rule_name = "suspicious_process"

    def run(self, context: DetectionContext) -> list[Alert]:
        event = context.event
        if event.event_type not in {"process_start", "command_execution"}:
            return []

        content = f"{json.dumps(context.details, ensure_ascii=True)} {event.raw_message or ''}".lower()
        matches = [hint for hint in SUSPICIOUS_PROCESS_HINTS if hint in content]
        if not matches:
            return []

        return [
            Alert(
                title="Suspicious process execution",
                description=(
                    "Command line or process metadata matched known attack tradecraft: "
                    + ", ".join(matches)
                ),
                severity="high",
                rule_name=self.rule_name,
                entity=event.host,
                event_id=event.id,
            )
        ]


class DetectionEngine:
    def __init__(self, rules: Sequence[DetectionRule]) -> None:
        self._rules = list(rules)

    def evaluate(self, session: Session, event: TelemetryEvent) -> list[Alert]:
        context = _build_context(session, event)
        generated: list[Alert] = []
        for rule in self._rules:
            generated.extend(rule.run(context))

        unique_alerts = []
        for alert in generated:
            if event.id is not None and _alert_exists(session, event.id, alert.rule_name):
                continue
            session.add(alert)
            unique_alerts.append(alert)
        return unique_alerts


def build_default_engine() -> DetectionEngine:
    return DetectionEngine(
        rules=[
            IOCMatchRule(),
            AuthBruteforceRule(),
            SuspiciousProcessRule(),
        ]
    )


DEFAULT_ENGINE = build_default_engine()


def evaluate_event(session: Session, event: TelemetryEvent) -> list[Alert]:
    return DEFAULT_ENGINE.evaluate(session, event)


def _build_context(session: Session, event: TelemetryEvent) -> DetectionContext:
    details = _parse_event_details(event.details)
    searchable_text = " ".join(
        part
        for part in [
            event.host,
            event.user or "",
            event.source_ip or "",
            json.dumps(details, ensure_ascii=True),
            event.raw_message or "",
        ]
        if part
    ).lower()
    return DetectionContext(
        session=session,
        event=event,
        searchable_text=searchable_text,
        details=details,
    )


def _parse_event_details(details: str) -> dict[str, object]:
    try:
        parsed = json.loads(details)
    except (TypeError, json.JSONDecodeError):
        return {}
    if isinstance(parsed, dict):
        return parsed
    return {}


def _alert_exists(session: Session, event_id: int, rule_name: str) -> bool:
    statement = select(Alert).where(Alert.event_id == event_id, Alert.rule_name == rule_name)
    return session.exec(statement).first() is not None


def _severity_from_confidence(confidence: int) -> str:
    if confidence >= 85:
        return "critical"
    if confidence >= 60:
        return "high"
    if confidence >= 35:
        return "medium"
    return "low"

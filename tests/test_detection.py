from datetime import timedelta

from sqlmodel import Session, SQLModel, create_engine

from src.models import IOC, TelemetryEvent, utc_now
from src.services.detection import evaluate_event


def _get_test_session() -> Session:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    return Session(engine)


def test_ioc_detection_creates_alert() -> None:
    with _get_test_session() as session:
        ioc = IOC(ioc_type="domain", value="evil.example", confidence=92)
        session.add(ioc)
        session.commit()

        event = TelemetryEvent(
            source="proxy",
            host="workstation-1",
            event_type="web_request",
            severity="medium",
            details='{"url": "https://evil.example/payload"}',
        )
        session.add(event)
        session.commit()
        session.refresh(event)

        alerts = evaluate_event(session, event)
        session.commit()

        assert len(alerts) == 1
        assert alerts[0].rule_name == "ioc_match"
        assert alerts[0].severity == "critical"


def test_bruteforce_detection_triggers_on_fifth_attempt() -> None:
    with _get_test_session() as session:
        base_time = utc_now()

        for idx in range(4):
            event = TelemetryEvent(
                timestamp=base_time + timedelta(seconds=idx),
                source="idp",
                host="auth-gateway",
                source_ip="203.0.113.10",
                event_type="auth_failed",
                severity="low",
                details='{"reason": "bad password"}',
            )
            session.add(event)
            session.commit()
            session.refresh(event)
            evaluate_event(session, event)
            session.commit()

        fifth_event = TelemetryEvent(
            timestamp=base_time + timedelta(seconds=4),
            source="idp",
            host="auth-gateway",
            source_ip="203.0.113.10",
            event_type="auth_failed",
            severity="low",
            details='{"reason": "bad password"}',
        )
        session.add(fifth_event)
        session.commit()
        session.refresh(fifth_event)

        alerts = evaluate_event(session, fifth_event)
        session.commit()

        assert len(alerts) == 1
        assert alerts[0].rule_name == "auth_bruteforce"
        assert alerts[0].entity == "203.0.113.10"

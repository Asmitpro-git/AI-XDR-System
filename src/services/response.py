from datetime import datetime, timezone

from src.models import Alert, ResponseAction

ALLOWED_ACTIONS = {
    "isolate_host": "Request EDR host isolation for the impacted endpoint.",
    "block_ip": "Push temporary firewall block for the suspicious source IP.",
    "disable_user": "Disable account pending incident triage.",
    "collect_forensics": "Collect volatile memory and recent process timeline.",
}


def queue_response_action(
    alert: Alert,
    action_type: str,
    notes: str | None = None,
) -> ResponseAction:
    if action_type not in ALLOWED_ACTIONS:
        raise ValueError(f"Unsupported action type: {action_type}")

    if alert.id is None:
        raise ValueError("Alert must be persisted before queuing a response action")

    alert.status = "investigating"
    return ResponseAction(
        alert_id=alert.id,
        action_type=action_type,
        notes=notes or ALLOWED_ACTIONS[action_type],
        status="queued",
    )


def mark_action_executed(action: ResponseAction) -> None:
    action.status = "executed"
    action.executed_at = datetime.now(timezone.utc)

"""Audit trail writer. Never stores secrets or record values."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.governance_models import AuditEvent

_SENSITIVE = ("password", "token", "secret", "authorization", "authorisation")


def sanitise(details: dict[str, object] | None) -> dict[str, object]:
    clean: dict[str, object] = {}
    for key, value in (details or {}).items():
        if any(part in key.lower() for part in _SENSITIVE):
            continue
        clean[key] = value if isinstance(value, (int, float, bool, type(None))) else str(value)[:300]
    return clean


def record_audit(
    session: Session,
    *,
    actor: str,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    outcome: str = "success",
    user_id: UUID | None = None,
    details: dict[str, object] | None = None,
) -> AuditEvent:
    """Add an audit event to the session; the caller commits."""
    event = AuditEvent(
        user_id=user_id,
        actor=actor[:320],
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        outcome=outcome,
        details=sanitise(details),
    )
    session.add(event)
    return event

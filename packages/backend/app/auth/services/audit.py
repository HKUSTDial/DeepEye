"""Auth audit logging service."""

import uuid

from fastapi import Request
from sqlalchemy.orm import Session

from app.repositories import AuthAuditRepository
from deepeye.utils.logger import logger


def log_auth_event(
    db: Session,
    *,
    event_type: str,
    success: bool,
    user_id: uuid.UUID | None = None,
    email: str | None = None,
    detail: str | None = None,
    request: Request | None = None,
) -> None:
    """Persist auth audit event without breaking primary request flow."""
    ip = request.client.host if request and request.client and request.client.host else None
    ua = request.headers.get("user-agent") if request else None
    try:
        AuthAuditRepository(db).log(
            event_type=event_type,
            success=success,
            user_id=user_id,
            email=email,
            ip_address=ip,
            user_agent=ua,
            detail=detail,
        )
    except Exception as exc:
        db.rollback()
        logger.exception("[auth-audit] failed to persist event %s: %s", event_type, exc)

"""Auth audit repository."""

import uuid

from sqlalchemy.orm import Session

from app.models import AuthAuditEvent
from app.repositories.base import SQLAlchemyRepository


class AuthAuditRepository(SQLAlchemyRepository[AuthAuditEvent, uuid.UUID]):
    """Repository for auth audit events."""

    def __init__(self, db: Session):
        super().__init__(db, AuthAuditEvent)

    def log(
        self,
        *,
        event_type: str,
        success: bool,
        user_id: uuid.UUID | None = None,
        email: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        detail: str | None = None,
    ) -> AuthAuditEvent:
        event = AuthAuditEvent(
            event_type=event_type,
            success=success,
            user_id=user_id,
            email=email,
            ip_address=ip_address,
            user_agent=user_agent,
            detail=detail,
        )
        return self.save(event)

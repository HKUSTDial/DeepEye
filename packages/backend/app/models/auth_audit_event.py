"""Auth audit event model."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class AuthAuditEvent(Base):
    """Security/audit events for auth flows."""

    __tablename__ = "auth_audit_events"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, index=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), default=None, nullable=True, index=True)
    email: Mapped[str | None] = mapped_column(String(255), default=None, nullable=True, index=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), default=None, nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), default=None, nullable=True)
    detail: Mapped[str | None] = mapped_column(String(1024), default=None, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc), index=True)

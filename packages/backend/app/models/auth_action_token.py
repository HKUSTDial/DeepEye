"""One-time auth action token model."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class AuthActionToken(Base):
    """One-time token for email verification/password reset."""

    __tablename__ = "auth_action_tokens"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    purpose: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    used_at: Mapped[datetime | None] = mapped_column(default=None, nullable=True, index=True)
    requested_by_ip: Mapped[str | None] = mapped_column(String(45), default=None, nullable=True)
    consumed_by_ip: Mapped[str | None] = mapped_column(String(45), default=None, nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), default=None, nullable=True)

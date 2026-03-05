"""Refresh token persistence model."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class RefreshToken(Base):
    """Issued refresh tokens for rotation/revocation."""

    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    token_jti: Mapped[uuid.UUID] = mapped_column(nullable=False, unique=True, index=True)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    revoked_at: Mapped[datetime | None] = mapped_column(default=None, nullable=True, index=True)
    replaced_by_token_jti: Mapped[uuid.UUID | None] = mapped_column(default=None, nullable=True)
    created_by_ip: Mapped[str | None] = mapped_column(String(45), default=None, nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), default=None, nullable=True)

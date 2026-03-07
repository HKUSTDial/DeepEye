import uuid
from datetime import datetime, timezone

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class SessionAttachment(Base):
    __tablename__ = "session_attachments"
    __table_args__ = (
        UniqueConstraint("session_id", "datasource_id", name="uq_session_attachment_session_datasource"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("chat_sessions.id"), nullable=False, index=True)
    datasource_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("data_sources.id"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))

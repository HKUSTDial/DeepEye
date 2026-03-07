import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import JSON, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class WorkflowDraft(Base):
    __tablename__ = "workflow_drafts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("chat_sessions.id"), nullable=False, index=True)
    turn_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("chat_turns.id"), nullable=True, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(32), default="workflow_agent")
    status: Mapped[str] = mapped_column(String(32), default="draft")
    file_path: Mapped[str | None] = mapped_column(String(512), nullable=True, index=True)
    definition: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    version: Mapped[int] = mapped_column(default=1)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    @property
    def display_name(self) -> str:
        if self.file_path:
            filename = self.file_path.rsplit("/", 1)[-1].strip()
            if filename.endswith(".json"):
                filename = filename[:-5]
            if filename:
                return filename
        return f"draft-{str(self.id)[:8]}"

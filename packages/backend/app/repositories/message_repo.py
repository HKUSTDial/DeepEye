"""Message Repository for session messages."""

from sqlalchemy import asc, func, select
from sqlalchemy.orm import Session

from app.models import SessionMessage
from app.schemas import Message


class MessageRepository:
    """Repository for session messages."""

    def __init__(self, db: Session):
        self.db = db

    def _next_seq(self, session_id: str) -> int:
        result = self.db.execute(
            select(func.coalesce(func.max(SessionMessage.sequence), 0)).where(
                SessionMessage.session_id == session_id
            )
        ).scalar()
        return (result or 0) + 1

    def append(self, session_id: str, message: Message) -> SessionMessage:
        """Append a message to the session."""
        msg = SessionMessage(
            session_id=session_id,
            sequence=self._next_seq(session_id),
            role=message.role,
            content=message.model_dump(),
        )
        self.db.add(msg)
        self.db.commit()
        self.db.refresh(msg)
        return msg

    def get_messages(self, session_id: str) -> list[dict]:
        """Get all messages for a session in order."""
        records = (
            self.db.query(SessionMessage)
            .filter(SessionMessage.session_id == session_id)
            .order_by(asc(SessionMessage.sequence))
            .all()
        )
        return [r.content for r in records]

    def delete_by_session(self, session_id: str) -> None:
        """Delete all messages for a session."""
        self.db.query(SessionMessage).filter(SessionMessage.session_id == session_id).delete()
        self.db.commit()

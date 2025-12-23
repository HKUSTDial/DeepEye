"""Event Repository - simple event store."""

from sqlalchemy import asc, func, select
from sqlalchemy.orm import Session

from app.models import AgentEventRecord


class EventRepository:
    """Event store for agent events."""

    def __init__(self, db: Session):
        self.db = db

    def _next_seq(self, session_id: str) -> int:
        result = self.db.execute(
            select(func.coalesce(func.max(AgentEventRecord.sequence), 0)).where(
                AgentEventRecord.session_id == session_id
            )
        ).scalar()
        return (result or 0) + 1

    def append(self, stream_id: str, event_type: str, source: str = "system", content: str | None = None, data: dict | None = None) -> None:
        self.db.add(AgentEventRecord(session_id=stream_id, sequence=self._next_seq(stream_id), event_type=event_type, source=source, content=content, data=data))
        self.db.commit()

    def get_stream(self, session_id: str) -> list[dict]:
        records = self.db.query(AgentEventRecord).filter(AgentEventRecord.session_id == session_id).order_by(asc(AgentEventRecord.sequence)).all()
        return [r.to_dict() for r in records]

    def delete_stream(self, session_id: str) -> None:
        self.db.query(AgentEventRecord).filter(AgentEventRecord.session_id == session_id).delete()
        self.db.commit()


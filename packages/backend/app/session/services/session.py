"""Session helpers."""

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session as DBSession

from app.models import ChatSession
from app.repositories import SessionRepository


def get_or_create_session(
    db: DBSession,
    user_id: uuid.UUID,
    session_id: str | None,
    title: str,
) -> tuple[ChatSession, str]:
    """Get owned session or create a new one for current user."""
    repo = SessionRepository(db)
    sid = session_id.strip() if session_id else ""

    if sid:
        try:
            sid_uuid = uuid.UUID(sid)
        except ValueError as exc:
            raise ValueError("Invalid session_id") from exc
        session = repo.get_by_id_and_user(sid_uuid, user_id)
        if not session:
            raise LookupError("Session not found")
        session.updated_at = datetime.now(timezone.utc)
        db.commit()
        return session, str(session.id)

    new_id = uuid.uuid4()
    session = repo.save(
        ChatSession(id=new_id, user_id=user_id, title=title[:50]),
    )
    return session, str(new_id)

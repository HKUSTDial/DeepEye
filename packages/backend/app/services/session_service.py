"""Session helpers."""

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session as DBSession

from app.models import ChatSession
from app.repositories import SessionRepository


def get_or_create_session(db: DBSession, session_id: str | None, title: str) -> tuple[ChatSession, str]:
    """Get existing session or create new one."""
    repo = SessionRepository(db)
    sid = session_id or str(uuid.uuid4())
    session = repo.get(uuid.UUID(sid))

    if not session:
        session = repo.save(ChatSession(id=uuid.UUID(sid), title=title[:50]))
    else:
        session.updated_at = datetime.now(timezone.utc)
        db.commit()

    return session, sid


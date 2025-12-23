"""Session Repository."""

import uuid

from sqlalchemy.orm import Session

from app.models import ChatSession
from app.repositories.base import SQLAlchemyRepository


class SessionRepository(SQLAlchemyRepository[ChatSession, uuid.UUID]):
    """Repository for ChatSession entities."""

    def __init__(self, db: Session):
        super().__init__(db, ChatSession)

    def list_recent(self, skip: int = 0, limit: int = 100) -> list[ChatSession]:
        """List sessions ordered by updated_at descending."""
        return self.find_all_desc("updated_at", skip, limit)


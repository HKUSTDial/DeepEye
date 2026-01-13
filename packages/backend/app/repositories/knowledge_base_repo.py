"""Knowledge base repository."""

import uuid

from sqlalchemy.orm import Session

from app.models.knowledge_base import KnowledgeBase
from app.repositories.base import SQLAlchemyRepository


class KnowledgeBaseRepository(SQLAlchemyRepository[KnowledgeBase, uuid.UUID]):
    def __init__(self, db: Session):
        super().__init__(db, KnowledgeBase)

    def list_by_user(self, user_id: uuid.UUID) -> list[KnowledgeBase]:
        return self.db.query(self.model_class).filter(KnowledgeBase.user_id == user_id).all()

    def get_by_id_and_user(self, kb_id: uuid.UUID, user_id: uuid.UUID) -> KnowledgeBase | None:
        return (
            self.db.query(self.model_class)
            .filter(KnowledgeBase.id == kb_id, KnowledgeBase.user_id == user_id)
            .first()
        )

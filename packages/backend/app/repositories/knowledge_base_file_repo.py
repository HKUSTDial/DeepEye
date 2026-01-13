"""Knowledge base file repository."""

import uuid

from sqlalchemy.orm import Session

from app.models.knowledge_base_file import KnowledgeBaseFile
from app.repositories.base import SQLAlchemyRepository


class KnowledgeBaseFileRepository(SQLAlchemyRepository[KnowledgeBaseFile, uuid.UUID]):
    def __init__(self, db: Session):
        super().__init__(db, KnowledgeBaseFile)

    def list_by_kb(self, kb_id: uuid.UUID, user_id: uuid.UUID) -> list[KnowledgeBaseFile]:
        return (
            self.db.query(self.model_class)
            .filter(KnowledgeBaseFile.kb_id == kb_id, KnowledgeBaseFile.user_id == user_id)
            .all()
        )

    def get_by_id_and_user(self, file_id: uuid.UUID, user_id: uuid.UUID) -> KnowledgeBaseFile | None:
        return (
            self.db.query(self.model_class)
            .filter(KnowledgeBaseFile.id == file_id, KnowledgeBaseFile.user_id == user_id)
            .first()
        )

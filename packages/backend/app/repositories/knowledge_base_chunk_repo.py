"""Knowledge base chunk repository."""

import uuid

from sqlalchemy.orm import Session

from app.models.knowledge_base_chunk import KnowledgeBaseChunk
from app.repositories.base import SQLAlchemyRepository


class KnowledgeBaseChunkRepository(SQLAlchemyRepository[KnowledgeBaseChunk, uuid.UUID]):
    def __init__(self, db: Session):
        super().__init__(db, KnowledgeBaseChunk)

    def list_by_file(self, file_id: uuid.UUID) -> list[KnowledgeBaseChunk]:
        return self.db.query(self.model_class).filter(KnowledgeBaseChunk.file_id == file_id).all()

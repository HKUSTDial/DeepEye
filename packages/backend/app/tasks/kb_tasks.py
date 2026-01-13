"""Knowledge base background tasks."""

import uuid

from app.core.celery_app import celery_app
from app.db.session import SessionLocal
from app.models.knowledge_base_file import KnowledgeBaseFile
from app.services.knowledge_base_service import process_kb_file


@celery_app.task(bind=True)
def process_kb_file_task(self, file_id: str) -> dict:
    db = SessionLocal()
    try:
        file_uuid = uuid.UUID(file_id)
        record = db.query(KnowledgeBaseFile).filter(KnowledgeBaseFile.id == file_uuid).first()
        if not record:
            return {"status": "error", "error": "File not found"}
        process_kb_file(db, record)
        return {"status": "ok", "file_id": file_id, "kb_id": str(record.kb_id)}
    finally:
        db.close()

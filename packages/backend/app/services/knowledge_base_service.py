from __future__ import annotations

import io
import os
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.config import settings
from app.models.knowledge_base import KnowledgeBase
from app.models.knowledge_base_chunk import KnowledgeBaseChunk
from app.models.knowledge_base_file import KnowledgeBaseFile
from app.services.minio_service import download_bytes, upload_bytes


def _storage_object_name(user_id: uuid.UUID, kb_id: uuid.UUID, file_id: uuid.UUID, filename: str) -> str:
    safe_name = filename.replace("\\", "_").replace("/", "_")
    return f"kb/{user_id}/{kb_id}/{file_id}/{safe_name}"


def create_kb_file_record(
    db: Session,
    user_id: uuid.UUID,
    kb: KnowledgeBase,
    filename: str,
    content_type: str | None,
    size_bytes: int,
) -> KnowledgeBaseFile:
    record = KnowledgeBaseFile(
        kb_id=kb.id,
        user_id=user_id,
        filename=filename,
        content_type=content_type,
        size_bytes=size_bytes,
        storage_path="pending",
        status="pending",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def upload_kb_file_to_storage(
    db: Session,
    record: KnowledgeBaseFile,
    user_id: uuid.UUID,
    kb_id: uuid.UUID,
    data: bytes,
    content_type: str | None,
) -> None:
    object_name = _storage_object_name(user_id, kb_id, record.id, record.filename)
    upload_bytes(settings.MINIO_KB_BUCKET, object_name, data, content_type)
    record.storage_path = object_name
    record.status = "uploaded"
    record.updated_at = datetime.now(timezone.utc)
    db.add(record)
    db.commit()


def _extract_text_from_bytes(filename: str, data: bytes) -> str:
    ext = os.path.splitext(filename.lower())[1]
    if ext in {".txt", ".md", ".csv", ".json"}:
        return data.decode("utf-8", errors="ignore")
    if ext == ".pdf":
        try:
            from pypdf import PdfReader

            reader = PdfReader(io.BytesIO(data))
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception:
            return ""
    if ext in {".docx", ".doc"}:
        try:
            from docx import Document

            doc = Document(io.BytesIO(data))
            return "\n".join(p.text for p in doc.paragraphs)
        except Exception:
            return ""
    return data.decode("utf-8", errors="ignore")


def _chunk_text(text: str, chunk_size: int = 1000, overlap: int = 100) -> list[str]:
    if not text:
        return []
    chunks: list[str] = []
    start = 0
    length = len(text)
    while start < length:
        end = min(start + chunk_size, length)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start = end - overlap if end - overlap > start else end
    return chunks


def process_kb_file(db: Session, file_record: KnowledgeBaseFile) -> None:
    file_record.status = "processing"
    file_record.error = None
    file_record.updated_at = datetime.now(timezone.utc)
    db.add(file_record)
    db.commit()

    try:
        raw = download_bytes(settings.MINIO_KB_BUCKET, file_record.storage_path)
        text = _extract_text_from_bytes(file_record.filename, raw)
        chunks = _chunk_text(text)
        if not chunks:
            raise ValueError("No text extracted from file.")

        db.query(KnowledgeBaseChunk).filter(
            KnowledgeBaseChunk.file_id == file_record.id
        ).delete(synchronize_session=False)

        for idx, chunk in enumerate(chunks):
            db.add(
                KnowledgeBaseChunk(
                    kb_id=file_record.kb_id,
                    file_id=file_record.id,
                    chunk_index=idx,
                    content=chunk,
                    created_at=datetime.now(timezone.utc),
                )
            )

        file_record.status = "ready"
        file_record.error = None
        file_record.updated_at = datetime.now(timezone.utc)
        db.add(file_record)
        db.commit()
    except Exception as exc:
        file_record.status = "failed"
        file_record.error = str(exc)
        file_record.updated_at = datetime.now(timezone.utc)
        db.add(file_record)
        db.commit()


def search_kb_chunks(
    db: Session,
    user_id: uuid.UUID,
    kb_ids: list[uuid.UUID],
    query: str,
    top_k: int = 5,
) -> list[dict]:
    if not kb_ids or not query.strip():
        return []
    like = f"%{query}%"
    rows = []
    try:
        # Enable pg_trgm for fuzzy matching when available.
        db.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
        stmt = text(
            """
            SELECT c.chunk_index,
                   c.content,
                   f.id AS file_id,
                   f.filename,
                   similarity(c.content, :query) AS score
            FROM knowledge_base_chunks c
            JOIN knowledge_base_files f ON f.id = c.file_id
            WHERE f.user_id = :user_id
              AND c.kb_id = ANY(:kb_ids)
              AND (c.content ILIKE :like OR similarity(c.content, :query) > :threshold)
            ORDER BY score DESC, c.chunk_index ASC
            LIMIT :limit
            """
        )
        result = db.execute(
            stmt,
            {
                "user_id": user_id,
                "kb_ids": kb_ids,
                "query": query,
                "like": like,
                "threshold": 0.1,
                "limit": top_k,
            },
        )
        rows = result.fetchall()
    except Exception:
        rows = (
            db.query(KnowledgeBaseChunk, KnowledgeBaseFile)
            .join(KnowledgeBaseFile, KnowledgeBaseChunk.file_id == KnowledgeBaseFile.id)
            .filter(KnowledgeBaseFile.user_id == user_id)
            .filter(KnowledgeBaseChunk.kb_id.in_(kb_ids))
            .filter(KnowledgeBaseChunk.content.ilike(like))
            .order_by(KnowledgeBaseChunk.chunk_index.asc())
            .limit(top_k)
            .all()
        )
    results: list[dict] = []
    for row in rows:
        mapping = getattr(row, "_mapping", None)
        if mapping and {"chunk_index", "content", "file_id", "filename"}.issubset(mapping.keys()):
            results.append(
                {
                    "file_id": mapping["file_id"],
                    "filename": mapping["filename"],
                    "chunk_index": mapping["chunk_index"],
                    "content": mapping["content"],
                }
            )
            continue
        if isinstance(row, tuple) and len(row) >= 4 and not isinstance(row[0], KnowledgeBaseChunk):
            chunk_index, content, file_id, filename = row[:4]
            results.append(
                {
                    "file_id": file_id,
                    "filename": filename,
                    "chunk_index": chunk_index,
                    "content": content,
                }
            )
        else:
            chunk, file = row
            results.append(
                {
                    "file_id": file.id,
                    "filename": file.filename,
                    "chunk_index": chunk.chunk_index,
                    "content": chunk.content,
                }
            )
    return results

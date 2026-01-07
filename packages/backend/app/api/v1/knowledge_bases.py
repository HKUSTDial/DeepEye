"""Knowledge base API endpoints."""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.knowledge_base import KnowledgeBase
from app.models.knowledge_base_chunk import KnowledgeBaseChunk
from app.models.knowledge_base_file import KnowledgeBaseFile
from app.repositories import KnowledgeBaseFileRepository, KnowledgeBaseRepository
from app.schemas.knowledge_base import (
    KnowledgeBaseCreate,
    KnowledgeBaseFileResponse,
    KnowledgeBaseResponse,
    KnowledgeBaseSearchRequest,
    KnowledgeBaseSearchResult,
    KnowledgeBaseUpdate,
)
from app.services.knowledge_base_service import (
    create_kb_file_record,
    upload_kb_file_to_storage,
    search_kb_chunks,
)
from app.services.minio_service import delete_object
from app.core.config import settings
from app.tasks.kb_tasks import process_kb_file_task

router = APIRouter(prefix="/knowledge-bases", tags=["knowledge-bases"])


@router.post("", response_model=KnowledgeBaseResponse, status_code=status.HTTP_201_CREATED)
def create_kb(payload: KnowledgeBaseCreate, request: Request, db: Session = Depends(get_db)):
    kb = KnowledgeBase(
        user_id=request.state.user_id,
        name=payload.name,
        description=payload.description,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(kb)
    db.commit()
    db.refresh(kb)
    return kb


@router.get("", response_model=list[KnowledgeBaseResponse])
def list_kbs(request: Request, db: Session = Depends(get_db)):
    return KnowledgeBaseRepository(db).list_by_user(request.state.user_id)


@router.get("/{kb_id}", response_model=KnowledgeBaseResponse)
def get_kb(kb_id: uuid.UUID, request: Request, db: Session = Depends(get_db)):
    kb = KnowledgeBaseRepository(db).get_by_id_and_user(kb_id, request.state.user_id)
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    return kb


@router.patch("/{kb_id}", response_model=KnowledgeBaseResponse)
def update_kb(
    kb_id: uuid.UUID,
    payload: KnowledgeBaseUpdate,
    request: Request,
    db: Session = Depends(get_db),
):
    repo = KnowledgeBaseRepository(db)
    kb = repo.get_by_id_and_user(kb_id, request.state.user_id)
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    if payload.name is not None:
        kb.name = payload.name
    if payload.description is not None:
        kb.description = payload.description
    kb.updated_at = datetime.now(timezone.utc)
    db.add(kb)
    db.commit()
    db.refresh(kb)
    return kb


@router.delete("/{kb_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_kb(kb_id: uuid.UUID, request: Request, db: Session = Depends(get_db)):
    repo = KnowledgeBaseRepository(db)
    kb = repo.get_by_id_and_user(kb_id, request.state.user_id)
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    files = db.query(KnowledgeBaseFile).filter(
        KnowledgeBaseFile.kb_id == kb_id,
        KnowledgeBaseFile.user_id == request.state.user_id,
    ).all()
    for record in files:
        delete_object(settings.MINIO_KB_BUCKET, record.storage_path)
    db.query(KnowledgeBaseChunk).filter(
        KnowledgeBaseChunk.kb_id == kb_id,
    ).delete(synchronize_session=False)
    db.query(KnowledgeBaseFile).filter(
        KnowledgeBaseFile.kb_id == kb_id,
        KnowledgeBaseFile.user_id == request.state.user_id,
    ).delete(synchronize_session=False)
    db.delete(kb)
    db.commit()
    return None


@router.post("/{kb_id}/files", response_model=KnowledgeBaseFileResponse, status_code=status.HTTP_201_CREATED)
async def upload_kb_file(
    kb_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
    file: UploadFile = File(...),
):
    kb = KnowledgeBaseRepository(db).get_by_id_and_user(kb_id, request.state.user_id)
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")

    data = await file.read()
    record = create_kb_file_record(
        db,
        request.state.user_id,
        kb,
        file.filename,
        file.content_type,
        len(data),
    )
    upload_kb_file_to_storage(db, record, request.state.user_id, kb.id, data, file.content_type)
    process_kb_file_task.delay(str(record.id))
    db.refresh(record)
    return record


@router.get("/{kb_id}/files", response_model=list[KnowledgeBaseFileResponse])
def list_kb_files(kb_id: uuid.UUID, request: Request, db: Session = Depends(get_db)):
    kb = KnowledgeBaseRepository(db).get_by_id_and_user(kb_id, request.state.user_id)
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    return KnowledgeBaseFileRepository(db).list_by_kb(kb_id, request.state.user_id)


@router.delete("/{kb_id}/files/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_kb_file(
    kb_id: uuid.UUID,
    file_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
):
    kb = KnowledgeBaseRepository(db).get_by_id_and_user(kb_id, request.state.user_id)
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    repo = KnowledgeBaseFileRepository(db)
    record = repo.get_by_id_and_user(file_id, request.state.user_id)
    if not record or record.kb_id != kb_id:
        raise HTTPException(status_code=404, detail="File not found")
    delete_object(settings.MINIO_KB_BUCKET, record.storage_path)
    db.query(KnowledgeBaseChunk).filter(
        KnowledgeBaseChunk.file_id == record.id,
    ).delete(synchronize_session=False)
    db.delete(record)
    db.commit()
    return None


@router.post("/{kb_id}/search", response_model=list[KnowledgeBaseSearchResult])
def search_kb(
    kb_id: uuid.UUID,
    payload: KnowledgeBaseSearchRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    kb = KnowledgeBaseRepository(db).get_by_id_and_user(kb_id, request.state.user_id)
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    results = search_kb_chunks(db, request.state.user_id, [kb_id], payload.query, payload.top_k)
    return results

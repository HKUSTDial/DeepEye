from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class KnowledgeBaseCreate(BaseModel):
    name: str
    description: str | None = None


class KnowledgeBaseUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class KnowledgeBaseResponse(BaseModel):
    id: UUID
    name: str
    description: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class KnowledgeBaseFileResponse(BaseModel):
    id: UUID
    kb_id: UUID
    filename: str
    content_type: str | None = None
    size_bytes: int
    status: str
    error: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class KnowledgeBaseSearchRequest(BaseModel):
    query: str
    top_k: int = 5


class KnowledgeBaseSearchResult(BaseModel):
    file_id: UUID
    filename: str
    chunk_index: int
    content: str

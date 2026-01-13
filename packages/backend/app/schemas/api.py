"""API Request/Response schemas"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None
    datasource_id: str | None = None
    kb_ids: list[str] | None = None


class ChatSessionResponse(BaseModel):
    id: UUID
    title: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# --- DataSource ---


class DataSourceBase(BaseModel):
    name: str
    type: str  # postgres, mysql, sqlite...
    connection_string: str


class DataSourceCreate(DataSourceBase):
    pass


class DataSourceUpdate(BaseModel):
    name: str | None = None
    type: str | None = None
    connection_string: str | None = None


class DataSourceResponse(DataSourceBase):
    id: UUID
    created_at: datetime

    model_config = {"from_attributes": True}

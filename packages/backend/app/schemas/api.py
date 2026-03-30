"""API Request/Response schemas"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None
    datasource_ids: list[str] | None = None


class ChatSessionResponse(BaseModel):
    id: UUID
    title: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# --- DataSource ---


class DataSourceBase(BaseModel):
    name: str
    type: str  # postgres, mysql, sqlite, csv, json...
    category: str = "database"  # database, file
    connection_string: str | None = None
    storage_path: str | None = None
    file_metadata: dict | None = None


class DataSourceCreate(BaseModel):
    name: str
    type: str
    connection_string: str


class DataSourceConnectionTestRequest(BaseModel):
    type: str
    connection_string: str


class DataSourceConnectionTestResponse(BaseModel):
    ok: bool
    type: str
    table_count: int
    sample_tables: list[str]


class DataSourcePreviewTable(BaseModel):
    name: str


class DataSourcePreviewColumn(BaseModel):
    name: str
    type: str


class DataSourcePreviewResponse(BaseModel):
    datasource_id: UUID
    datasource_name: str
    category: str
    tables: list[DataSourcePreviewTable]
    table: str | None = None
    columns: list[DataSourcePreviewColumn]
    rows: list[dict[str, Any]]
    page: int
    page_size: int
    total_rows: int
    total_pages: int


class DataSourceUpdate(BaseModel):
    name: str | None = None
    type: str | None = None
    category: str | None = None
    connection_string: str | None = None
    storage_path: str | None = None
    file_metadata: dict | None = None


class DataSourceResponse(DataSourceBase):
    id: UUID
    created_at: datetime

    model_config = {"from_attributes": True}

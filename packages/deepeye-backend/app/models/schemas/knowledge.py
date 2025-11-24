"""Knowledge Base schemas."""

from datetime import datetime
from typing import List, Optional, Dict, Any, Union
from uuid import UUID

from pydantic import BaseModel, Field

# --- File Metadata Schemas ---

class FileMetadataBase(BaseModel):
    summary: Optional[str] = Field(None, description="Summary of the file content")
    column_metadata: Optional[Dict[str, Dict[str, Any]]] = Field(None, description="Column metadata for structured files")
    annotations: Optional[str] = Field(None, description="Manual annotations for unstructured files")

class FileMetadataCreate(FileMetadataBase):
    pass

class FileMetadataUpdate(FileMetadataBase):
    pass

class FileMetadataResponse(FileMetadataBase):
    id: UUID
    file_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# --- Database Knowledge Schemas ---

# Column Description
class ColumnDescriptionBase(BaseModel):
    column_name: str
    description: Optional[str] = None

class ColumnDescriptionCreate(ColumnDescriptionBase):
    pass

class ColumnDescriptionUpdate(BaseModel):
    description: Optional[str] = None

class ColumnDescriptionResponse(ColumnDescriptionBase):
    id: UUID
    table_description_id: UUID
    position: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Table Description
class TableDescriptionBase(BaseModel):
    schema_name: str = "public"
    table_name: str
    description: Optional[str] = None

class TableDescriptionCreate(TableDescriptionBase):
    pass

class TableDescriptionUpdate(BaseModel):
    description: Optional[str] = None

class TableDescriptionResponse(TableDescriptionBase):
    id: UUID
    connection_id: UUID
    columns: List[ColumnDescriptionResponse] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Business Rule
class BusinessRuleBase(BaseModel):
    rule_name: str
    description: str
    rule_sql_snippet: Optional[str] = None

class BusinessRuleCreate(BusinessRuleBase):
    pass

class BusinessRuleUpdate(BaseModel):
    rule_name: Optional[str] = None
    description: Optional[str] = None
    rule_sql_snippet: Optional[str] = None

class BusinessRuleResponse(BusinessRuleBase):
    id: UUID
    connection_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Business Metric
class BusinessMetricBase(BaseModel):
    name: str
    alias: Optional[List[str]] = None
    description: str
    definition_type: str = Field(..., pattern="^(SQL_FRAGMENT|NATURAL_LANGUAGE|DERIVED)$")
    definition_sql: Optional[str] = None

class BusinessMetricCreate(BusinessMetricBase):
    pass

class BusinessMetricUpdate(BaseModel):
    name: Optional[str] = None
    alias: Optional[List[str]] = None
    description: Optional[str] = None
    definition_type: Optional[str] = None
    definition_sql: Optional[str] = None

class BusinessMetricResponse(BusinessMetricBase):
    id: UUID
    connection_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Example Query (Memory)
class ExampleQueryBase(BaseModel):
    question: str
    sql_logic: str

class ExampleQueryCreate(ExampleQueryBase):
    pass

class ExampleQueryResponse(ExampleQueryBase):
    id: UUID
    connection_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


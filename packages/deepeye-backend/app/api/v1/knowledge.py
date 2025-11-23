from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID

from app.db.session import get_db
from app.models.database import User
from app.api.v1.auth import get_current_user
from app.models.schemas.knowledge import (
    FileMetadataCreate,
    FileMetadataUpdate,
    FileMetadataResponse,
    TableDescriptionResponse,
    TableDescriptionUpdate,
    ColumnDescriptionUpdate,
    ColumnDescriptionResponse,
    BusinessRuleCreate,
    BusinessRuleUpdate,
    BusinessRuleResponse,
    BusinessMetricCreate,
    BusinessMetricUpdate,
    BusinessMetricResponse,
    ExampleQueryCreate,
    ExampleQueryResponse,
)
from app.services import knowledge_service

router = APIRouter()

# --- File Metadata Endpoints ---

@router.post("/file/{file_id}", response_model=FileMetadataResponse)
async def upsert_file_metadata(
    file_id: UUID,
    metadata: FileMetadataCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create or update file metadata."""
    return await knowledge_service.upsert_file_metadata(db, file_id, metadata, current_user.id)

@router.get("/file/{file_id}", response_model=FileMetadataResponse)
async def get_file_metadata(
    file_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get file metadata."""
    return await knowledge_service.get_file_metadata(db, file_id, current_user.id)

# --- Database Knowledge Endpoints ---

@router.post("/database/{connection_id}/sync", response_model=List[TableDescriptionResponse])
async def sync_database_schema(
    connection_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Sync database schema to populate table descriptions."""
    return await knowledge_service.sync_database_schema(db, connection_id, current_user.id)

@router.get("/database/{connection_id}/tables", response_model=List[TableDescriptionResponse])
async def get_database_tables(
    connection_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all table descriptions for a connection."""
    return await knowledge_service.get_tables_by_connection(db, connection_id, current_user.id)


@router.put("/database/tables/{table_id}", response_model=TableDescriptionResponse)
async def update_table_description(
    table_id: UUID,
    description: TableDescriptionUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update table description."""
    return await knowledge_service.update_table_description(db, table_id, description, current_user.id)

@router.put("/database/columns/{column_id}", response_model=ColumnDescriptionResponse)
async def update_column_description(
    column_id: UUID,
    description: ColumnDescriptionUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update column description."""
    return await knowledge_service.update_column_description(db, column_id, description, current_user.id)

# --- Business Rules ---

@router.post("/database/{connection_id}/rules", response_model=BusinessRuleResponse)
async def create_business_rule(
    connection_id: UUID,
    rule: BusinessRuleCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a business rule."""
    return await knowledge_service.create_business_rule(db, connection_id, rule, current_user.id)

@router.put("/database/rules/{rule_id}", response_model=BusinessRuleResponse)
async def update_business_rule(
    rule_id: UUID,
    rule: BusinessRuleUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a business rule."""
    return await knowledge_service.update_business_rule(db, rule_id, rule, current_user.id)

@router.delete("/database/rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_business_rule(
    rule_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a business rule."""
    await knowledge_service.delete_business_rule(db, rule_id, current_user.id)

# --- Business Metrics ---

@router.post("/database/{connection_id}/metrics", response_model=BusinessMetricResponse)
async def create_business_metric(
    connection_id: UUID,
    metric: BusinessMetricCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a business metric."""
    return await knowledge_service.create_business_metric(db, connection_id, metric, current_user.id)

@router.put("/database/metrics/{metric_id}", response_model=BusinessMetricResponse)
async def update_business_metric(
    metric_id: UUID,
    metric: BusinessMetricUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a business metric."""
    return await knowledge_service.update_business_metric(db, metric_id, metric, current_user.id)

@router.delete("/database/metrics/{metric_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_business_metric(
    metric_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a business metric."""
    await knowledge_service.delete_business_metric(db, metric_id, current_user.id)

# --- Example Queries (Memory) ---

@router.post("/database/{connection_id}/examples", response_model=ExampleQueryResponse)
async def create_example_query(
    connection_id: UUID,
    example: ExampleQueryCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create an example query (Memory)."""
    return await knowledge_service.create_example_query(db, connection_id, example, current_user.id)

@router.delete("/database/examples/{example_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_example_query(
    example_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete an example query."""
    await knowledge_service.delete_example_query(db, example_id, current_user.id)


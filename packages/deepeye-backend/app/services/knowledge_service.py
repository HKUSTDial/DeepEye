from typing import List, Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.database import (
    File,
    FileMetadata,
    DatabaseConnection,
    TableDescription,
    ColumnDescription,
    BusinessRule,
    BusinessMetric,
    ExampleQuery,
)
from app.models.schemas.knowledge import (
    FileMetadataCreate,
    FileMetadataUpdate,
    TableDescriptionUpdate,
    ColumnDescriptionUpdate,
    BusinessRuleCreate,
    BusinessRuleUpdate,
    BusinessMetricCreate,
    BusinessMetricUpdate,
    ExampleQueryCreate,
)


# --- File Metadata Services ---

async def upsert_file_metadata(
    db: AsyncSession, file_id: UUID, metadata: FileMetadataCreate, user_id: str
) -> FileMetadata:
    # Verify file ownership
    query = select(File).where(File.id == str(file_id), File.user_id == user_id)
    result = await db.execute(query)
    file = result.scalar_one_or_none()
    
    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="File not found or permission denied"
        )

    # Check if metadata exists
    query = select(FileMetadata).where(FileMetadata.file_id == str(file_id))
    result = await db.execute(query)
    existing_metadata = result.scalar_one_or_none()

    if existing_metadata:
        # Update
        update_data = metadata.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(existing_metadata, field, value)
        await db.commit()
        await db.refresh(existing_metadata)
        return existing_metadata
    else:
        # Create
        new_metadata = FileMetadata(file_id=str(file_id), **metadata.model_dump())
        db.add(new_metadata)
        await db.commit()
        await db.refresh(new_metadata)
        return new_metadata


async def get_file_metadata(db: AsyncSession, file_id: UUID, user_id: str) -> FileMetadata:
    # Verify file ownership
    query = select(File).where(File.id == str(file_id), File.user_id == user_id)
    result = await db.execute(query)
    file = result.scalar_one_or_none()
    
    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="File not found or permission denied"
        )

    query = select(FileMetadata).where(FileMetadata.file_id == str(file_id))
    result = await db.execute(query)
    metadata = result.scalar_one_or_none()
    
    if not metadata:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Metadata not found for this file"
        )
        
    return metadata


# --- Database Knowledge Services ---

async def _verify_connection_access(db: AsyncSession, connection_id: UUID, user_id: str) -> DatabaseConnection:
    query = select(DatabaseConnection).where(
        DatabaseConnection.id == str(connection_id), DatabaseConnection.user_id == user_id
    )
    result = await db.execute(query)
    connection = result.scalar_one_or_none()
    
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Database connection not found or permission denied"
        )
    return connection


async def sync_database_schema(db: AsyncSession, connection_id: UUID, user_id: str) -> List[TableDescription]:
    connection = await _verify_connection_access(db, connection_id, user_id)
    
    # TODO: In a real implementation, this would connect to the actual DB and reflect metadata.
    # For now, we will just return existing table descriptions or empty list if implemented later.
    # To fully implement, we need 'sqlalchemy.inspect(engine)' on the target DB.
    
    # This is a placeholder for the actual sync logic. 
    # Current implementation just returns what is already in DB to avoid errors.
    
    stmt = select(TableDescription).options(selectinload(TableDescription.columns)).where(
        TableDescription.connection_id == str(connection_id)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_tables_by_connection(db: AsyncSession, connection_id: UUID, user_id: str) -> List[TableDescription]:
    await _verify_connection_access(db, connection_id, user_id)
    
    stmt = select(TableDescription).options(selectinload(TableDescription.columns)).where(
        TableDescription.connection_id == str(connection_id)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def update_table_description(
    db: AsyncSession, table_id: UUID, description_update: TableDescriptionUpdate, user_id: str
) -> TableDescription:
    # We need to join with Connection to verify user access
    stmt = (
        select(TableDescription)
        .join(DatabaseConnection)
        .where(
            TableDescription.id == str(table_id),
            DatabaseConnection.user_id == user_id
        )
        .options(selectinload(TableDescription.columns))
    )
    result = await db.execute(stmt)
    table_desc = result.scalar_one_or_none()
    
    if not table_desc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Table description not found"
        )
        
    update_data = description_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(table_desc, field, value)
        
    await db.commit()
    await db.refresh(table_desc)
    return table_desc


async def update_column_description(
    db: AsyncSession, column_id: UUID, description_update: ColumnDescriptionUpdate, user_id: str
) -> ColumnDescription:
    stmt = (
        select(ColumnDescription)
        .join(TableDescription)
        .join(DatabaseConnection)
        .where(
            ColumnDescription.id == str(column_id),
            DatabaseConnection.user_id == user_id
        )
    )
    result = await db.execute(stmt)
    column_desc = result.scalar_one_or_none()
    
    if not column_desc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Column description not found"
        )
        
    update_data = description_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(column_desc, field, value)
        
    await db.commit()
    await db.refresh(column_desc)
    return column_desc


# --- Business Rules Services ---

async def create_business_rule(
    db: AsyncSession, connection_id: UUID, rule: BusinessRuleCreate, user_id: str
) -> BusinessRule:
    await _verify_connection_access(db, connection_id, user_id)
    
    new_rule = BusinessRule(connection_id=str(connection_id), **rule.model_dump())
    db.add(new_rule)
    await db.commit()
    await db.refresh(new_rule)
    return new_rule


async def update_business_rule(
    db: AsyncSession, rule_id: UUID, rule_update: BusinessRuleUpdate, user_id: str
) -> BusinessRule:
    stmt = (
        select(BusinessRule)
        .join(DatabaseConnection)
        .where(
            BusinessRule.id == str(rule_id),
            DatabaseConnection.user_id == user_id
        )
    )
    result = await db.execute(stmt)
    rule = result.scalar_one_or_none()
    
    if not rule:
        raise HTTPException(status_code=404, detail="Business rule not found")
        
    update_data = rule_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(rule, field, value)
        
    await db.commit()
    await db.refresh(rule)
    return rule


async def delete_business_rule(db: AsyncSession, rule_id: UUID, user_id: str) -> None:
    stmt = (
        select(BusinessRule)
        .join(DatabaseConnection)
        .where(
            BusinessRule.id == str(rule_id),
            DatabaseConnection.user_id == user_id
        )
    )
    result = await db.execute(stmt)
    rule = result.scalar_one_or_none()
    
    if not rule:
        raise HTTPException(status_code=404, detail="Business rule not found")
        
    await db.delete(rule)
    await db.commit()


# --- Business Metrics Services ---

async def create_business_metric(
    db: AsyncSession, connection_id: UUID, metric: BusinessMetricCreate, user_id: str
) -> BusinessMetric:
    await _verify_connection_access(db, connection_id, user_id)
    
    new_metric = BusinessMetric(connection_id=str(connection_id), **metric.model_dump())
    db.add(new_metric)
    await db.commit()
    await db.refresh(new_metric)
    return new_metric


async def update_business_metric(
    db: AsyncSession, metric_id: UUID, metric_update: BusinessMetricUpdate, user_id: str
) -> BusinessMetric:
    stmt = (
        select(BusinessMetric)
        .join(DatabaseConnection)
        .where(
            BusinessMetric.id == str(metric_id),
            DatabaseConnection.user_id == user_id
        )
    )
    result = await db.execute(stmt)
    metric = result.scalar_one_or_none()
    
    if not metric:
        raise HTTPException(status_code=404, detail="Business metric not found")
        
    update_data = metric_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(metric, field, value)
        
    await db.commit()
    await db.refresh(metric)
    return metric


async def delete_business_metric(db: AsyncSession, metric_id: UUID, user_id: str) -> None:
    stmt = (
        select(BusinessMetric)
        .join(DatabaseConnection)
        .where(
            BusinessMetric.id == str(metric_id),
            DatabaseConnection.user_id == user_id
        )
    )
    result = await db.execute(stmt)
    metric = result.scalar_one_or_none()
    
    if not metric:
        raise HTTPException(status_code=404, detail="Business metric not found")
        
    await db.delete(metric)
    await db.commit()


# --- Example Query Services ---

async def create_example_query(
    db: AsyncSession, connection_id: UUID, example: ExampleQueryCreate, user_id: str
) -> ExampleQuery:
    await _verify_connection_access(db, connection_id, user_id)
    
    new_example = ExampleQuery(connection_id=str(connection_id), **example.model_dump())
    db.add(new_example)
    await db.commit()
    await db.refresh(new_example)
    return new_example


async def delete_example_query(db: AsyncSession, example_id: UUID, user_id: str) -> None:
    stmt = (
        select(ExampleQuery)
        .join(DatabaseConnection)
        .where(
            ExampleQuery.id == str(example_id),
            DatabaseConnection.user_id == user_id
        )
    )
    result = await db.execute(stmt)
    example = result.scalar_one_or_none()
    
    if not example:
        raise HTTPException(status_code=404, detail="Example query not found")
        
    await db.delete(example)
    await db.commit()


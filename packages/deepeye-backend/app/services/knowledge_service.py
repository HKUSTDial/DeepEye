from typing import List, Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import delete, select, inspect, create_engine
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


def _get_db_url(connection: DatabaseConnection) -> str:
    """Construct database URL from connection details."""
    if connection.type == "postgres" or connection.type == "postgresql":
        return f"postgresql://{connection.username}:{connection.password}@{connection.host}:{connection.port}/{connection.database}"
    elif connection.type == "mysql":
        return f"mysql+pymysql://{connection.username}:{connection.password}@{connection.host}:{connection.port}/{connection.database}"
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unsupported database type: {connection.type}"
        )


async def sync_database_schema(db: AsyncSession, connection_id: UUID, user_id: str) -> List[TableDescription]:
    connection = await _verify_connection_access(db, connection_id, user_id)
    
    # 1. Build DB URL
    try:
        db_url = _get_db_url(connection)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    # 2. Inspect Database (Sync operation, could be blocking so ideally run in threadpool)
    # Since we don't have celery, we'll run it synchronously for now, or use asyncio.to_thread if available
    import asyncio
    
    def inspect_schema():
        engine = create_engine(db_url)
        inspector = inspect(engine)
        tables = []
        for table_name in inspector.get_table_names():
            columns = []
            for col in inspector.get_columns(table_name):
                columns.append({
                    "name": col["name"],
                    "type": str(col["type"]),  # Store type as string description
                    "comment": col.get("comment")
                })
            
            table_comment = inspector.get_table_comment(table_name).get("text")
            tables.append({
                "name": table_name,
                "comment": table_comment,
                "columns": columns
            })
        return tables

    try:
        # Run inspection in thread pool to avoid blocking async loop
        tables_info = await asyncio.to_thread(inspect_schema)
    except Exception as e:
         raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=f"Failed to connect to database or inspect schema: {str(e)}"
        )

    # 3. Update/Create Records in DeepEye DB
    # Fetch existing tables to avoid duplicates or to update them
    existing_tables_stmt = select(TableDescription).options(selectinload(TableDescription.columns)).where(
        TableDescription.connection_id == str(connection_id)
    )
    result = await db.execute(existing_tables_stmt)
    existing_tables = {t.table_name: t for t in result.scalars().all()}
    
    synced_tables = []

    for table_info in tables_info:
        t_name = table_info["name"]
        t_desc = table_info["comment"]
        
        # Upsert Table
        is_new_table = False
        if t_name in existing_tables:
            table_obj = existing_tables[t_name]
            # Only update description if it's currently empty and we found one in DB
            if not table_obj.description and t_desc:
                table_obj.description = t_desc
        else:
            is_new_table = True
            table_obj = TableDescription(
                connection_id=str(connection_id),
                table_name=t_name,
                description=t_desc,
                schema_name="public" # Defaulting to public for now
            )
            db.add(table_obj)
            await db.flush() # Flush to get ID
            
        synced_tables.append(table_obj)
        
        # Upsert Columns
        # For existing tables, columns are already loaded via selectinload
        # For new tables, we need to explicitly load or use empty dict (new tables have no existing columns)
        if is_new_table:
            # New table, no existing columns
            existing_columns = {}
        else:
            # Existing table, columns are already loaded via selectinload
            existing_columns = {c.column_name: c for c in table_obj.columns} if table_obj.columns else {}
        
        for col_position, col_info in enumerate(table_info["columns"]):
            c_name = col_info["name"]
            c_desc = col_info["comment"]
            # We could also store the type if we added a type field to ColumnDescription
            
            if c_name in existing_columns:
                col_obj = existing_columns[c_name]
                # Update position if it has changed (e.g., table was altered)
                if col_obj.position != col_position:
                    col_obj.position = col_position
                if not col_obj.description and c_desc:
                    col_obj.description = c_desc
            else:
                col_obj = ColumnDescription(
                    table_description_id=table_obj.id,
                    column_name=c_name,
                    description=c_desc,
                    position=col_position
                )
                db.add(col_obj)

    await db.commit()
    
    # Refresh to return full objects with relationships loaded
    # Re-query to ensure relationships are properly loaded in async context
    # This is especially important for newly created tables to avoid lazy loading issues
    table_ids = [t.id for t in synced_tables]
    if table_ids:
        refresh_stmt = (
            select(TableDescription)
            .options(selectinload(TableDescription.columns))
            .where(TableDescription.id.in_(table_ids))
        )
        result = await db.execute(refresh_stmt)
        refreshed_tables = {t.id: t for t in result.scalars().all()}
        
        # Verify all tables were found after commit
        if len(refreshed_tables) != len(synced_tables):
            missing_ids = set(table_ids) - set(refreshed_tables.keys())
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to refresh all tables after commit. Missing table IDs: {missing_ids}"
            )
        
        # Return in the same order as synced_tables, ensuring all tables are included with relationships loaded
        return [refreshed_tables[t.id] for t in synced_tables]
    
    return synced_tables


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

async def get_business_rules(
    db: AsyncSession, connection_id: UUID, user_id: str
) -> List[BusinessRule]:
    await _verify_connection_access(db, connection_id, user_id)
    
    stmt = (
        select(BusinessRule)
        .where(BusinessRule.connection_id == str(connection_id))
        .order_by(BusinessRule.created_at.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


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

async def get_business_metrics(
    db: AsyncSession, connection_id: UUID, user_id: str
) -> List[BusinessMetric]:
    await _verify_connection_access(db, connection_id, user_id)
    
    stmt = (
        select(BusinessMetric)
        .where(BusinessMetric.connection_id == str(connection_id))
        .order_by(BusinessMetric.created_at.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


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

async def get_example_queries(
    db: AsyncSession, connection_id: UUID, user_id: str
) -> List[ExampleQuery]:
    await _verify_connection_access(db, connection_id, user_id)
    
    stmt = (
        select(ExampleQuery)
        .where(ExampleQuery.connection_id == str(connection_id))
        .order_by(ExampleQuery.created_at.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


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

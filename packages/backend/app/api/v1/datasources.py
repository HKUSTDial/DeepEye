"""DataSource API endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from sqlalchemy.orm import Session

from app.core.deps import CurrentUserId
from app.db.session import get_db
from app.models import DataSource
from app.repositories import DataSourceRepository
from app.schemas import DataSourceCreate, DataSourceResponse, DataSourceUpdate, SandboxEvent, SandboxEventType
from app.services.datasource_file_service import create_file_datasource
from app.infra.event_bus import RedisEventBus
from app.core.config import settings

router = APIRouter(prefix="/datasources", tags=["datasources"])


@router.get("", response_model=list[DataSourceResponse])
def list_datasources(
    user_id: CurrentUserId,  # ⭐ 自动鉴权并注入 user_id
    db: Session = Depends(get_db)
):
    """List all datasources for current user."""
    return DataSourceRepository(db).find_by_user(user_id)


@router.post("", response_model=DataSourceResponse)
def create_datasource(
    data: DataSourceCreate,
    user_id: CurrentUserId,  # ⭐ 自动鉴权并注入 user_id
    db: Session = Depends(get_db)
):
    """Create a new database datasource for current user (MySQL, PostgreSQL, SQLite, etc.)."""
    conn = (data.connection_string or "").strip()
    if not conn:
        raise HTTPException(status_code=400, detail="connection_string is required for database datasource")
    entity = DataSource(
        user_id=user_id,
        name=(data.name or "").strip() or data.type,
        type=(data.type or "mysql").strip().lower(),
        category="database",
        connection_string=conn,
    )
    return DataSourceRepository(db).save(entity)


@router.post("/upload", response_model=DataSourceResponse)
async def upload_datasource_file(
    user_id: CurrentUserId,
    file: UploadFile = File(...),
    session_id: str | None = None,
    db: Session = Depends(get_db)
):
    """Upload a data file (csv, json, xlsx) as a datasource."""
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")
    
    ds = create_file_datasource(
        db=db,
        user_id=user_id,
        filename=file.filename,
        data=data,
        content_type=file.content_type
    )

    # Proactive Sync: Push to sandbox if session_id is provided
    if session_id:
        from app.sandbox.manager import sandbox_manager
        try:
            sandbox = await sandbox_manager.get_or_create_sandbox(session_id)
            dest_path = f"/workspace/data/{file.filename}"
            await sandbox.write_file(dest_path, data)
            
            # Notify frontend about file change via event bus
            event_bus = RedisEventBus(settings.REDIS_URL)
            await event_bus.publish(
                f"session:{session_id}",
                SandboxEvent(type=SandboxEventType.FILES_CHANGED, source="sandbox").model_dump_json()
            )
            await event_bus.close()
        except Exception as e:
            # We don't fail the upload if sandbox sync fails, just log it
            from deepeye.utils.logger import logger
            logger.error(f"Proactive sync failed for session {session_id}: {e}")

    return ds


@router.get("/{datasource_id}", response_model=DataSourceResponse)
def get_datasource(
    datasource_id: uuid.UUID,
    user_id: CurrentUserId,  # ⭐ 自动鉴权并注入 user_id
    db: Session = Depends(get_db)
):
    """Get a datasource by ID (only if owned by current user)."""
    entity = DataSourceRepository(db).get_by_id_and_user(datasource_id, user_id)
    if not entity:
        raise HTTPException(status_code=404, detail="DataSource not found")
    return entity


@router.patch("/{datasource_id}", response_model=DataSourceResponse)
def update_datasource(
    datasource_id: uuid.UUID,
    data: DataSourceUpdate,
    user_id: CurrentUserId,
    db: Session = Depends(get_db),
):
    """Update a datasource (only database: name, type, connection_string)."""
    entity = DataSourceRepository(db).get_by_id_and_user(datasource_id, user_id)
    if not entity:
        raise HTTPException(status_code=404, detail="DataSource not found")
    if data.name is not None:
        entity.name = data.name.strip() or entity.name
    if data.type is not None:
        entity.type = data.type.strip().lower()
    if data.connection_string is not None:
        conn = data.connection_string.strip()
        if not conn and getattr(entity, "category", None) == "database":
            raise HTTPException(status_code=400, detail="connection_string cannot be empty for database datasource")
        entity.connection_string = conn if conn else entity.connection_string
    db.add(entity)
    db.commit()
    db.refresh(entity)
    return entity


@router.get("/{datasource_id}/tables")
def list_datasource_tables(
    datasource_id: uuid.UUID,
    user_id: CurrentUserId,
    db: Session = Depends(get_db),
):
    """List tables (and columns) for a database datasource. Only for category=database."""
    ds = DataSourceRepository(db).get_by_id_and_user(datasource_id, user_id)
    if not ds:
        raise HTTPException(status_code=404, detail="DataSource not found")
    if getattr(ds, "category", "database") != "database":
        raise HTTPException(status_code=400, detail="Tables can only be listed for database datasources")
    if not ds.connection_string:
        raise HTTPException(status_code=400, detail="Datasource has no connection_string")
    try:
        from sqlalchemy import create_engine, inspect
        from app.node.utils import normalize_connection_string
        engine = create_engine(normalize_connection_string(ds.connection_string))
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        result = []
        for name in tables[:50]:  # limit 50 tables
            columns = inspector.get_columns(name)
            result.append({
                "name": name,
                "columns": [{"name": c.get("name"), "type": str(c.get("type", ""))} for c in columns],
            })
        return {"datasource_id": str(ds.id), "datasource_name": ds.name, "tables": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to connect or list tables: {str(e)}")


@router.delete("/{datasource_id}")
async def delete_datasource(
    datasource_id: uuid.UUID,
    user_id: CurrentUserId,
    session_id: str | None = None,
    db: Session = Depends(get_db)
):
    """Delete a datasource (only if owned by current user)."""
    repo = DataSourceRepository(db)
    ds = repo.get_by_id_and_user(datasource_id, user_id)
    if not ds:
        raise HTTPException(status_code=404, detail="DataSource not found")

    # If it's a file datasource, cleanup storage
    if ds.category == "file" and ds.storage_path:
        from app.services.minio_service import delete_object
        from deepeye.utils.logger import logger
        
        # 1. Delete from MinIO
        try:
            delete_object(settings.MINIO_DATASOURCE_BUCKET, ds.storage_path)
        except Exception as e:
            logger.error(f"Failed to delete file from MinIO: {e}")

        # 2. Delete from Sandbox if session_id is provided
        if session_id:
            from app.sandbox.manager import sandbox_manager
            try:
                sandbox = await sandbox_manager.get_or_create_sandbox(session_id)
                from app.sandbox.manager import _get_datasource_filename
                original_filename = _get_datasource_filename(ds)
                dest_path = f"/workspace/data/{original_filename}"
                await sandbox.exec_command(f"rm {dest_path}")
                
                # Notify frontend about file change
                event_bus = RedisEventBus(settings.REDIS_URL)
                await event_bus.publish(
                    f"session:{session_id}",
                    SandboxEvent(type=SandboxEventType.FILES_CHANGED, source="sandbox").model_dump_json()
                )
                await event_bus.close()
            except Exception as e:
                logger.error(f"Failed to delete file from sandbox {session_id}: {e}")

    repo.delete(datasource_id)
    return {"status": "ok"}


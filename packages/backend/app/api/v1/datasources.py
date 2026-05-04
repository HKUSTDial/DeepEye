"""DataSource API endpoints."""

import shlex
import uuid

from fastapi import APIRouter, Depends, HTTPException, File, Query, UploadFile
from sqlalchemy.orm import Session

from app.core.deps import CurrentUserId
from app.db.session import get_db
from app.models import DataSource
from app.repositories import DataSourceRepository, SessionAttachmentRepository, SessionRepository
from app.schemas import (
    DataSourceConnectionTestRequest,
    DataSourceConnectionTestResponse,
    DataSourceCreate,
    DataSourcePreviewResponse,
    DataSourceResponse,
    DataSourceUpdate,
    SandboxEvent,
    SandboxEventType,
)
from app.datasource.services.connection import validate_database_connection
from app.datasource.services.file import create_file_datasource
from app.datasource.services.preview import build_datasource_preview
from app.datasource.services.specs import (
    DataSourceCategory,
    get_datasource_filename,
    normalize_datasource_category,
    normalize_datasource_type,
    validate_database_datasource_type,
    validate_file_type,
    workspace_data_path,
)
from app.infra.event_bus import RedisEventBus
from app.core.config import settings
from app.session.services.attachment import attach_datasource_to_session

router = APIRouter(prefix="/datasources", tags=["datasources"])


def _get_owned_session_or_404(db: Session, session_id: str, user_id: uuid.UUID):
    try:
        session_uuid = uuid.UUID(session_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid session_id") from exc

    session = SessionRepository(db).get_by_id_and_user(session_uuid, user_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.get("", response_model=list[DataSourceResponse])
def list_datasources(
    user_id: CurrentUserId,  # ⭐ 自动鉴权并注入 user_id
    db: Session = Depends(get_db)
):
    """List all datasources for current user."""
    return DataSourceRepository(db).find_by_user(user_id)


@router.post("/test-connection", response_model=DataSourceConnectionTestResponse)
def test_datasource_connection(
    data: DataSourceConnectionTestRequest,
    user_id: CurrentUserId,
):
    """Test a database datasource connection before saving it."""
    del user_id
    try:
        result = validate_database_connection(
            connection_string=data.connection_string,
            datasource_type=data.type,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return DataSourceConnectionTestResponse(**result)


@router.post("", response_model=DataSourceResponse)
async def create_datasource(
    data: DataSourceCreate,
    user_id: CurrentUserId,  # ⭐ 自动鉴权并注入 user_id
    session_id: str | None = None,
    db: Session = Depends(get_db)
):
    """Create a new database datasource for current user (MySQL, PostgreSQL, SQLite, etc.)."""
    conn = (data.connection_string or "").strip()
    if not conn:
        raise HTTPException(status_code=400, detail="connection_string is required for database datasource")
    ds_type = normalize_datasource_type(data.type or "mysql")
    try:
        validate_database_datasource_type(ds_type)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    try:
        validate_database_connection(connection_string=conn, datasource_type=ds_type)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    entity = DataSource(
        user_id=user_id,
        name=(data.name or "").strip() or ds_type,
        type=ds_type,
        category="database",
        connection_string=conn,
    )
    created = DataSourceRepository(db).save(entity)
    if session_id:
        session = _get_owned_session_or_404(db, session_id, user_id)
        await attach_datasource_to_session(db, session, created)
    return created


@router.post("/upload", response_model=DataSourceResponse)
async def upload_datasource_file(
    user_id: CurrentUserId,
    file: UploadFile = File(...),
    session_id: str | None = None,
    db: Session = Depends(get_db)
):
    """Upload a data file (csv, json, xlsx, xls, parquet) as a datasource."""
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")
    session = _get_owned_session_or_404(db, session_id, user_id) if session_id else None
    try:
        ds = create_file_datasource(
            db=db,
            user_id=user_id,
            filename=file.filename,
            data=data,
            content_type=file.content_type
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    if session:
        await attach_datasource_to_session(db, session, ds)

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
    if data.category is not None:
        try:
            next_category = normalize_datasource_category(data.category)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        if next_category != entity.category:
            raise HTTPException(status_code=400, detail="Changing datasource category is not supported")
    if data.type is not None:
        next_type = normalize_datasource_type(data.type)
        try:
            if entity.category == DataSourceCategory.DATABASE.value:
                validate_database_datasource_type(next_type)
            else:
                validate_file_type(next_type)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        entity.type = next_type
    if data.connection_string is not None:
        conn = data.connection_string.strip()
        if not conn and getattr(entity, "category", None) == "database":
            raise HTTPException(status_code=400, detail="connection_string cannot be empty for database datasource")
        try:
            validate_database_connection(connection_string=conn or entity.connection_string or "", datasource_type=entity.type)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
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
        from app.infra.db import normalize_connection_string
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


@router.get("/{datasource_id}/preview", response_model=DataSourcePreviewResponse)
def preview_datasource(
    datasource_id: uuid.UUID,
    user_id: CurrentUserId,
    table: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Preview one datasource with paginated rows. Database datasources can switch tables."""
    ds = DataSourceRepository(db).get_by_id_and_user(datasource_id, user_id)
    if not ds:
        raise HTTPException(status_code=404, detail="DataSource not found")

    try:
        return build_datasource_preview(
            datasource=ds,
            table_name=table,
            page=page,
            page_size=page_size,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


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
        from app.infra.services.minio import delete_object
        from deepeye.utils.logger import logger
        
        # 1. Delete from MinIO
        try:
            delete_object(settings.MINIO_DATA_BUCKET, ds.storage_path)
        except Exception as e:
            logger.error(f"Failed to delete file from MinIO: {e}")

        # 2. Delete from Sandbox if session_id is provided
        if session_id:
            from app.sandbox.manager import sandbox_manager
            try:
                sandbox = await sandbox_manager.get_or_create_sandbox(session_id)
                original_filename = get_datasource_filename(getattr(ds, "name", None), getattr(ds, "storage_path", None))
                dest_path = workspace_data_path(original_filename)
                await sandbox.exec_command(f"rm -f -- {shlex.quote(dest_path)}")
                
                # Notify frontend about file change
                event_bus = RedisEventBus(settings.REDIS_URL)
                await event_bus.publish(
                    f"session:{session_id}",
                    SandboxEvent(type=SandboxEventType.FILES_CHANGED, source="sandbox").model_dump_json()
                )
                await event_bus.close()
            except Exception as e:
                logger.error(f"Failed to delete file from sandbox {session_id}: {e}")

    SessionAttachmentRepository(db).detach_all_for_datasource(datasource_id)
    repo.delete(datasource_id)
    return {"status": "ok"}

"""DataSource API endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import CurrentUserId
from app.db.session import get_db
from app.models import DataSource
from app.repositories import DataSourceRepository
from app.schemas import DataSourceCreate, DataSourceResponse

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
    """Create a new datasource for current user."""
    entity = DataSource(
        user_id=user_id,
        name=data.name,
        type=data.type,
        connection_string=data.connection_string
    )
    return DataSourceRepository(db).save(entity)


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


@router.delete("/{datasource_id}")
def delete_datasource(
    datasource_id: uuid.UUID,
    user_id: CurrentUserId,  # ⭐ 自动鉴权并注入 user_id
    db: Session = Depends(get_db)
):
    """Delete a datasource (only if owned by current user)."""
    repo = DataSourceRepository(db)
    if not repo.get_by_id_and_user(datasource_id, user_id):
        raise HTTPException(status_code=404, detail="DataSource not found")
    repo.delete(datasource_id)
    return {"status": "ok"}


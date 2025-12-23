"""DataSource API endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import DataSource
from app.repositories import DataSourceRepository
from app.schemas import DataSourceCreate, DataSourceResponse

router = APIRouter(prefix="/datasources", tags=["datasources"])


@router.get("", response_model=list[DataSourceResponse])
def list_datasources(db: Session = Depends(get_db)):
    return DataSourceRepository(db).find_all()


@router.post("", response_model=DataSourceResponse)
def create_datasource(data: DataSourceCreate, db: Session = Depends(get_db)):
    entity = DataSource(name=data.name, type=data.type, connection_string=data.connection_string)
    return DataSourceRepository(db).save(entity)


@router.get("/{datasource_id}", response_model=DataSourceResponse)
def get_datasource(datasource_id: uuid.UUID, db: Session = Depends(get_db)):
    entity = DataSourceRepository(db).get(datasource_id)
    if not entity:
        raise HTTPException(status_code=404, detail="DataSource not found")
    return entity


@router.delete("/{datasource_id}")
def delete_datasource(datasource_id: uuid.UUID, db: Session = Depends(get_db)):
    repo = DataSourceRepository(db)
    if not repo.get(datasource_id):
        raise HTTPException(status_code=404, detail="DataSource not found")
    repo.delete(datasource_id)
    return {"status": "ok"}


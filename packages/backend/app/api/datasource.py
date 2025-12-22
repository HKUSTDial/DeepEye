from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import uuid

from app.db.session import get_db
from app.models.datasource import DataSource
from app.api.schemas import DataSourceCreate, DataSourceResponse, DataSourceUpdate

router = APIRouter()

@router.get("/datasources", response_model=List[DataSourceResponse])
def list_datasources(db: Session = Depends(get_db)):
    return db.query(DataSource).all()

@router.post("/datasources", response_model=DataSourceResponse)
def create_datasource(datasource: DataSourceCreate, db: Session = Depends(get_db)):
    db_obj = DataSource(
        name=datasource.name,
        type=datasource.type,
        connection_string=datasource.connection_string
    )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    # Convert UUID to str for Pydantic
    db_obj.id = str(db_obj.id)
    return db_obj

@router.get("/datasources/{datasource_id}", response_model=DataSourceResponse)
def get_datasource(datasource_id: str, db: Session = Depends(get_db)):
    db_obj = db.query(DataSource).filter(DataSource.id == datasource_id).first()
    if not db_obj:
        raise HTTPException(status_code=404, detail="DataSource not found")
    db_obj.id = str(db_obj.id)
    return db_obj

@router.delete("/datasources/{datasource_id}")
def delete_datasource(datasource_id: str, db: Session = Depends(get_db)):
    db_obj = db.query(DataSource).filter(DataSource.id == datasource_id).first()
    if not db_obj:
        raise HTTPException(status_code=404, detail="DataSource not found")
    db.delete(db_obj)
    db.commit()
    return {"status": "ok"}


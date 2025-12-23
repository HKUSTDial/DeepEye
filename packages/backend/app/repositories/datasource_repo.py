"""DataSource Repository."""

import uuid

from sqlalchemy.orm import Session

from app.models import DataSource
from app.repositories.base import SQLAlchemyRepository


class DataSourceRepository(SQLAlchemyRepository[DataSource, uuid.UUID]):
    def __init__(self, db: Session):
        super().__init__(db, DataSource)


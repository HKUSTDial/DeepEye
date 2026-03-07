"""DataSource Repository."""

import uuid

from sqlalchemy.orm import Session

from app.models import DataSource
from app.repositories.base import SQLAlchemyRepository


class DataSourceRepository(SQLAlchemyRepository[DataSource, uuid.UUID]):
    def __init__(self, db: Session):
        super().__init__(db, DataSource)
    
    def find_by_user(self, user_id: uuid.UUID) -> list[DataSource]:
        """Find all datasources for a specific user."""
        return self.db.query(self.model_class).filter(DataSource.user_id == user_id).all()
    
    def get_by_id_and_user(self, datasource_id: uuid.UUID | str, user_id: uuid.UUID | str) -> DataSource | None:
        """Get a datasource by ID, but only if it belongs to the specified user."""
        if isinstance(datasource_id, str):
            datasource_id = uuid.UUID(datasource_id)
        if isinstance(user_id, str):
            user_id = uuid.UUID(user_id)
        return (
            self.db.query(self.model_class)
            .filter(DataSource.id == datasource_id, DataSource.user_id == user_id)
            .first()
        )

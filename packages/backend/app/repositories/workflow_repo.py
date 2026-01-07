"""Workflow repository."""

import uuid

from sqlalchemy.orm import Session

from app.models.workflow import Workflow
from app.repositories.base import SQLAlchemyRepository


class WorkflowRepository(SQLAlchemyRepository[Workflow, uuid.UUID]):
    def __init__(self, db: Session):
        super().__init__(db, Workflow)

    def list_by_user(self, user_id: uuid.UUID) -> list[Workflow]:
        return self.db.query(self.model_class).filter(Workflow.user_id == user_id).all()

    def get_by_id_and_user(self, workflow_id: uuid.UUID, user_id: uuid.UUID) -> Workflow | None:
        return (
            self.db.query(self.model_class)
            .filter(Workflow.id == workflow_id, Workflow.user_id == user_id)
            .first()
        )

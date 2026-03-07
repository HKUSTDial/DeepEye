"""Workflow artifact repository."""

import uuid

from sqlalchemy.orm import Session

from app.models.workflow_artifact import WorkflowArtifact
from app.repositories.base import SQLAlchemyRepository


class WorkflowArtifactRepository(SQLAlchemyRepository[WorkflowArtifact, uuid.UUID]):
    def __init__(self, db: Session):
        super().__init__(db, WorkflowArtifact)

    def list_by_run(self, run_id: uuid.UUID) -> list[WorkflowArtifact]:
        return (
            self.db.query(self.model_class)
            .filter(WorkflowArtifact.run_id == run_id)
            .order_by(WorkflowArtifact.created_at.asc())
            .all()
        )

    def list_by_turn(self, turn_id: uuid.UUID) -> list[WorkflowArtifact]:
        return (
            self.db.query(self.model_class)
            .filter(WorkflowArtifact.turn_id == turn_id)
            .order_by(WorkflowArtifact.created_at.asc())
            .all()
        )

    def delete_by_run(self, run_id: uuid.UUID) -> int:
        deleted = self.db.query(self.model_class).filter(WorkflowArtifact.run_id == run_id).delete()
        self.db.commit()
        return deleted

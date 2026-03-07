"""Workflow run repository."""

import uuid
from sqlalchemy import desc

from sqlalchemy.orm import Session

from app.models.workflow_run import WorkflowRun
from app.repositories.base import SQLAlchemyRepository


class WorkflowRunRepository(SQLAlchemyRepository[WorkflowRun, uuid.UUID]):
    def __init__(self, db: Session):
        super().__init__(db, WorkflowRun)

    def list_by_user(self, user_id: uuid.UUID) -> list[WorkflowRun]:
        return self.db.query(self.model_class).filter(WorkflowRun.user_id == user_id).all()

    def get_by_id_and_user(self, run_id: uuid.UUID, user_id: uuid.UUID) -> WorkflowRun | None:
        return (
            self.db.query(self.model_class)
            .filter(WorkflowRun.id == run_id, WorkflowRun.user_id == user_id)
            .first()
        )

    def get_latest_by_turn(self, turn_id: uuid.UUID) -> WorkflowRun | None:
        return (
            self.db.query(self.model_class)
            .filter(WorkflowRun.turn_id == turn_id)
            .order_by(desc(WorkflowRun.created_at))
            .first()
        )

    def get_latest_by_session(self, session_id: uuid.UUID) -> WorkflowRun | None:
        return (
            self.db.query(self.model_class)
            .filter(WorkflowRun.session_id == session_id)
            .order_by(desc(WorkflowRun.created_at))
            .first()
        )

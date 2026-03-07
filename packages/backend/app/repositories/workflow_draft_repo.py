"""Workflow draft repository."""

import uuid

from sqlalchemy.orm import Session

from app.models.workflow_draft import WorkflowDraft
from app.repositories.base import SQLAlchemyRepository


class WorkflowDraftRepository(SQLAlchemyRepository[WorkflowDraft, uuid.UUID]):
    def __init__(self, db: Session):
        super().__init__(db, WorkflowDraft)

    def list_by_session(self, session_id: uuid.UUID, limit: int = 50) -> list[WorkflowDraft]:
        return (
            self.db.query(self.model_class)
            .filter(WorkflowDraft.session_id == session_id)
            .order_by(WorkflowDraft.updated_at.desc())
            .limit(limit)
            .all()
        )

    def get_latest_by_session(self, session_id: uuid.UUID) -> WorkflowDraft | None:
        return (
            self.db.query(self.model_class)
            .filter(WorkflowDraft.session_id == session_id)
            .order_by(WorkflowDraft.updated_at.desc())
            .first()
        )

    def get_latest_by_turn(self, turn_id: uuid.UUID) -> WorkflowDraft | None:
        return (
            self.db.query(self.model_class)
            .filter(WorkflowDraft.turn_id == turn_id)
            .order_by(WorkflowDraft.updated_at.desc())
            .first()
        )

    def get_latest_by_session_and_path(self, session_id: uuid.UUID, file_path: str) -> WorkflowDraft | None:
        return (
            self.db.query(self.model_class)
            .filter(WorkflowDraft.session_id == session_id, WorkflowDraft.file_path == file_path)
            .order_by(WorkflowDraft.updated_at.desc())
            .first()
        )

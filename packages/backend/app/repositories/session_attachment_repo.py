"""Session attachment repository."""

import uuid

from sqlalchemy.orm import Session

from app.models import DataSource, SessionAttachment
from app.repositories.base import SQLAlchemyRepository


class SessionAttachmentRepository(SQLAlchemyRepository[SessionAttachment, uuid.UUID]):
    def __init__(self, db: Session):
        super().__init__(db, SessionAttachment)

    def get_by_session_and_datasource(
        self,
        session_id: uuid.UUID,
        datasource_id: uuid.UUID,
    ) -> SessionAttachment | None:
        return (
            self.db.query(self.model_class)
            .filter(
                SessionAttachment.session_id == session_id,
                SessionAttachment.datasource_id == datasource_id,
            )
            .first()
        )

    def attach(self, session_id: uuid.UUID, datasource_id: uuid.UUID) -> SessionAttachment:
        existing = self.get_by_session_and_datasource(session_id, datasource_id)
        if existing:
            return existing
        return self.save(SessionAttachment(session_id=session_id, datasource_id=datasource_id))

    def list_datasources(self, session_id: uuid.UUID) -> list[DataSource]:
        return (
            self.db.query(DataSource)
            .join(SessionAttachment, SessionAttachment.datasource_id == DataSource.id)
            .filter(SessionAttachment.session_id == session_id)
            .order_by(SessionAttachment.created_at.asc())
            .all()
        )

    def list_datasource_ids(self, session_id: uuid.UUID) -> list[str]:
        rows = (
            self.db.query(SessionAttachment.datasource_id)
            .filter(SessionAttachment.session_id == session_id)
            .order_by(SessionAttachment.created_at.asc())
            .all()
        )
        return [str(row[0]) for row in rows]

    def detach(self, session_id: uuid.UUID, datasource_id: uuid.UUID) -> bool:
        attachment = self.get_by_session_and_datasource(session_id, datasource_id)
        if not attachment:
            return False
        self.db.delete(attachment)
        self.db.commit()
        return True

    def detach_all_for_session(self, session_id: uuid.UUID) -> int:
        deleted = (
            self.db.query(SessionAttachment)
            .filter(SessionAttachment.session_id == session_id)
            .delete(synchronize_session=False)
        )
        self.db.commit()
        return deleted

    def detach_all_for_datasource(self, datasource_id: uuid.UUID) -> int:
        deleted = (
            self.db.query(SessionAttachment)
            .filter(SessionAttachment.datasource_id == datasource_id)
            .delete(synchronize_session=False)
        )
        self.db.commit()
        return deleted

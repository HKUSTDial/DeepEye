"""Session attachment helpers."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session as DBSession

from app.core.config import settings
from app.infra.event_bus import RedisEventBus
from app.models import ChatSession, DataSource
from app.repositories import SessionAttachmentRepository
from app.sandbox import sandbox_manager
from app.schemas import SandboxEvent, SandboxEventType
from deepeye.utils.logger import logger


def list_session_attachments(db: DBSession, session_id: uuid.UUID) -> list[DataSource]:
    return SessionAttachmentRepository(db).list_datasources(session_id)


def get_session_attachment_ids(db: DBSession, session_id: uuid.UUID) -> list[str]:
    return SessionAttachmentRepository(db).list_datasource_ids(session_id)


async def attach_datasource_to_session(
    db: DBSession,
    session: ChatSession,
    datasource: DataSource,
) -> DataSource:
    repo = SessionAttachmentRepository(db)
    repo.attach(session.id, datasource.id)
    session.updated_at = datetime.now(timezone.utc)
    db.add(session)
    db.commit()

    if getattr(datasource, "category", None) == "file":
        await _sync_file_datasource(session.id, datasource)
    return datasource


async def detach_datasource_from_session(
    db: DBSession,
    session: ChatSession,
    datasource: DataSource,
) -> bool:
    detached = SessionAttachmentRepository(db).detach(session.id, datasource.id)
    if detached and getattr(datasource, "category", None) == "file":
        await _remove_file_datasource(session.id, datasource)
    if detached:
        session.updated_at = datetime.now(timezone.utc)
        db.add(session)
        db.commit()
    return detached


async def _sync_file_datasource(session_id: uuid.UUID, datasource: DataSource) -> None:
    if not getattr(datasource, "storage_path", None):
        return
    try:
        await sandbox_manager.sync_datasource_files(str(session_id), [datasource])
        await _publish_files_changed(session_id)
    except Exception as exc:
        logger.error(
            "Failed to sync datasource %s to sandbox for session %s: %s",
            datasource.id,
            session_id,
            exc,
        )


async def _remove_file_datasource(session_id: uuid.UUID, datasource: DataSource) -> None:
    if not getattr(datasource, "storage_path", None):
        return
    try:
        await sandbox_manager.remove_datasource_file(str(session_id), datasource)
        await _publish_files_changed(session_id)
    except Exception as exc:
        logger.error(
            "Failed to remove datasource %s from sandbox for session %s: %s",
            datasource.id,
            session_id,
            exc,
        )


async def _publish_files_changed(session_id: uuid.UUID) -> None:
    event_bus = RedisEventBus(settings.REDIS_URL)
    try:
        await event_bus.publish(
            f"session:{session_id}",
            SandboxEvent(type=SandboxEventType.FILES_CHANGED, source="sandbox").model_dump_json(),
        )
    finally:
        await event_bus.close()

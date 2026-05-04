from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from app.db.session import SessionLocal
from app.repositories import SessionRepository
from app.workflow.services.file_service import service_run_workflow_draft, service_run_workflow_from_file
from app.workflow.services.targets import resolve_workflow_target, save_workflow_draft
from deepeye.utils.logger import logger


@dataclass(frozen=True)
class WorkflowAgentRunOutcome:
    raw_result: dict[str, Any] | None = None
    draft_id: str | None = None
    workflow_definition: dict[str, Any] | None = None
    error_type: str | None = None
    error_summary: str | None = None
    error: str | None = None
    repairable: bool = False

    @property
    def is_failure(self) -> bool:
        return self.error is not None


def get_workflow_session(db, session_id: str):
    try:
        session_uuid = uuid.UUID(session_id)
    except (TypeError, ValueError):
        logger.warning("[workflow_agent_runs] Invalid session_id=%s", session_id)
        return None
    return SessionRepository(db).get(session_uuid)


def _session_not_found(draft_id: str | None = None) -> WorkflowAgentRunOutcome:
    return WorkflowAgentRunOutcome(
        draft_id=draft_id,
        error_type="session_not_found",
        error_summary="Session not found.",
        repairable=False,
        error="Session not found.",
    )


def _draft_not_found(draft_id: str | None = None) -> WorkflowAgentRunOutcome:
    return WorkflowAgentRunOutcome(
        draft_id=draft_id,
        error_type="draft_not_found",
        error_summary="Workflow draft not found.",
        repairable=False,
        error="Workflow draft not found.",
    )


async def run_agent_workflow_file(
    *,
    session_id: str,
    file_path: str,
    turn_id: str | None = None,
) -> dict[str, Any]:
    db = SessionLocal()
    try:
        session = get_workflow_session(db, session_id)
        if not session:
            return {"status": "error", "error": "Session not found."}
        _, norm_path = resolve_workflow_target(
            db,
            session_id,
            file_path=file_path,
        )
        return await service_run_workflow_from_file(
            db,
            session.user_id,
            session_id,
            norm_path,
            turn_id=turn_id,
        )
    finally:
        db.close()


async def run_agent_workflow_draft(
    *,
    session_id: str,
    draft_id: str,
    turn_id: str | None = None,
) -> WorkflowAgentRunOutcome:
    db = SessionLocal()
    try:
        session = get_workflow_session(db, session_id)
        if not session:
            return _session_not_found(draft_id)
        try:
            existing_draft, _ = resolve_workflow_target(
                db,
                session_id,
                draft_id=draft_id,
            )
        except ValueError:
            return _draft_not_found(draft_id)
        if not existing_draft or not isinstance(existing_draft.definition, dict):
            return _draft_not_found(draft_id)
        resolved_draft_id = str(existing_draft.id)
        workflow_definition = existing_draft.definition
        result = await service_run_workflow_draft(
            db,
            session.user_id,
            session_id,
            resolved_draft_id,
            turn_id=turn_id,
        )
        return WorkflowAgentRunOutcome(
            raw_result=result,
            draft_id=resolved_draft_id,
            workflow_definition=workflow_definition,
        )
    finally:
        db.close()


async def create_and_run_agent_workflow_draft(
    *,
    session_id: str,
    definition: dict[str, Any],
    turn_id: str | None = None,
    draft_id: str | None = None,
    file_path: str | None = None,
    name: str | None = None,
) -> WorkflowAgentRunOutcome:
    db = SessionLocal()
    try:
        session = get_workflow_session(db, session_id)
        if not session:
            return _session_not_found(draft_id)
        draft = save_workflow_draft(
            db,
            session_id=session_id,
            user_id=str(session.user_id),
            definition=definition,
            turn_id=turn_id,
            draft_id=draft_id,
            file_path=file_path,
            name=name,
            source="workflow_agent",
        )
        saved_draft_id = str(draft.id)
        result = await service_run_workflow_draft(
            db,
            session.user_id,
            session_id,
            saved_draft_id,
            turn_id=turn_id,
        )
        return WorkflowAgentRunOutcome(
            raw_result=result,
            draft_id=saved_draft_id,
            workflow_definition=definition,
        )
    finally:
        db.close()

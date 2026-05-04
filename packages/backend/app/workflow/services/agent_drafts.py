from __future__ import annotations

import json
import shlex
from dataclasses import dataclass
from typing import Any, Literal

from app.db.session import SessionLocal
from app.sandbox import sandbox_manager
from app.workflow.services.file_service import write_workflow_definition_to_file
from app.workflow.services.targets import normalize_workflow_path, resolve_workflow_target, save_workflow_draft


@dataclass(frozen=True)
class WorkflowDraftSaveResult:
    draft_id: str
    file_path: str


@dataclass(frozen=True)
class WorkflowDefinitionReadResult:
    status: Literal["success", "error"]
    workflow: dict[str, Any] | None = None
    draft_id: str | None = None
    error: str | None = None

    def to_tool_response(self) -> dict[str, Any]:
        response: dict[str, Any] = {"status": self.status}
        if self.draft_id is not None:
            response["draft_id"] = self.draft_id
        if self.workflow is not None:
            response["workflow"] = self.workflow
        if self.error:
            response["error"] = self.error
        return response


async def save_agent_workflow_draft(
    *,
    session_id: str,
    user_id: str,
    definition: dict[str, Any],
    turn_id: str | None = None,
    draft_id: str | None = None,
    file_path: str | None = None,
    name: str | None = None,
) -> WorkflowDraftSaveResult:
    db = SessionLocal()
    try:
        draft = save_workflow_draft(
            db,
            session_id=session_id,
            user_id=user_id,
            definition=definition,
            turn_id=turn_id,
            draft_id=draft_id,
            file_path=file_path,
            name=name,
            source="workflow_agent",
        )
        saved_draft_id = str(draft.id)
        saved_file_path = draft.file_path or normalize_workflow_path(file_path or name or "workflow.json")
    finally:
        db.close()

    await write_workflow_definition_to_file(session_id, saved_file_path, definition)
    return WorkflowDraftSaveResult(draft_id=saved_draft_id, file_path=saved_file_path)


async def read_workflow_file(session_id: str, path: str) -> dict[str, Any]:
    sandbox = await sandbox_manager.get_or_create_sandbox(session_id)
    if not sandbox:
        raise ValueError("failed to get or create sandbox")
    result = await sandbox.exec_command(f"cat {shlex.quote(path)}")
    if result.exit_code != 0:
        raise ValueError(result.stderr or "failed to read workflow file")
    if not result.stdout.strip():
        raise ValueError("workflow file is empty")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid workflow json: {exc}") from exc


async def read_workflow_definition(
    *,
    session_id: str,
    draft_id: str | None = None,
    file_path: str | None = None,
) -> WorkflowDefinitionReadResult:
    if not draft_id and not file_path:
        return WorkflowDefinitionReadResult(
            status="error",
            error="Provide draft_id. Use file_path only for an explicit legacy workflow file.",
        )

    db = SessionLocal()
    try:
        existing_draft, norm_path = resolve_workflow_target(
            db,
            session_id,
            draft_id=draft_id,
            file_path=file_path,
        )
        if existing_draft and isinstance(existing_draft.definition, dict) and existing_draft.definition:
            return WorkflowDefinitionReadResult(
                status="success",
                workflow=existing_draft.definition,
                draft_id=str(existing_draft.id),
            )
    finally:
        db.close()

    try:
        workflow = await read_workflow_file(session_id, norm_path)
        return WorkflowDefinitionReadResult(status="success", workflow=workflow, draft_id=draft_id)
    except Exception as exc:
        return WorkflowDefinitionReadResult(status="error", error=str(exc), draft_id=draft_id)

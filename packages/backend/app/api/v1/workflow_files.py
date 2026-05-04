"""Workflow file execution endpoints."""

import uuid

from fastapi import APIRouter, Depends
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import CurrentUserId
from app.db.session import get_db
from app.repositories import SessionRepository
from app.schemas.workflow import WorkflowFileRunRequest
from app.workflow.services.file_service import load_workflow_definition_from_file, prepare_tracked_workflow_file_run
from app.tasks.workflow_tasks import run_workflow_file_task

router = APIRouter(prefix="/workflow-files", tags=["workflow-files"])


@router.post("/run")
async def run_from_file(
    request: WorkflowFileRunRequest,
    user_id: CurrentUserId,
    db: Session = Depends(get_db),
):
    session_uuid = uuid.UUID(request.session_id)
    session = SessionRepository(db).get_by_id_and_user(session_uuid, user_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    definition = await load_workflow_definition_from_file(request.session_id, request.path)
    tracked_turn, tracked_draft, tracked_run = prepare_tracked_workflow_file_run(
        db,
        user_id=session.user_id,
        session_id=str(session.id),
        path=request.path,
        definition=definition,
    )
    task = run_workflow_file_task.delay(
        str(session.user_id),
        str(session.id),
        request.path,
        str(tracked_turn.id) if tracked_turn else None,
        str(tracked_draft.id) if tracked_draft else None,
        str(tracked_run.id) if tracked_run else None,
    )
    return {
        "status": "queued",
        "task_id": task.id,
        "turn_id": str(tracked_turn.id) if tracked_turn else None,
        "draft_id": str(tracked_draft.id) if tracked_draft else None,
        "run_id": str(tracked_run.id) if tracked_run else None,
    }

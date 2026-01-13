"""Workflow file execution endpoints."""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.workflow import WorkflowFileRunRequest
from app.tasks.workflow_tasks import run_workflow_file_task

router = APIRouter(prefix="/workflow-files", tags=["workflow-files"])


@router.post("/run")
async def run_from_file(request: WorkflowFileRunRequest, http_request: Request, db: Session = Depends(get_db)):
    user_id = http_request.state.user_id
    task = run_workflow_file_task.delay(user_id, request.session_id, request.path)
    return {"status": "queued", "task_id": task.id}

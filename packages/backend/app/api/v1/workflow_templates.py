"""Workflow templates API endpoints."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.workflow import Workflow
from app.models.workflow_run import WorkflowRun
from app.repositories import WorkflowRepository, WorkflowRunRepository
from app.schemas.workflow import WorkflowTemplateResponse, WorkflowTemplateRunRequest, WorkflowRunResponse
from app.services.workflow_templates import apply_defaults, get_template, list_templates, render_template, validate_params
from app.tasks.workflow_tasks import run_workflow_task

router = APIRouter(prefix="/workflow-templates", tags=["workflow-templates"])


@router.get("", response_model=list[WorkflowTemplateResponse])
def list_workflow_templates():
    return list_templates()


@router.post("/{template_id}/runs", response_model=WorkflowRunResponse, status_code=status.HTTP_201_CREATED)
def run_template(
    template_id: str,
    payload: WorkflowTemplateRunRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    template = get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    params = apply_defaults(template, payload.params or {})
    missing = validate_params(template, params)
    if missing:
        raise HTTPException(status_code=400, detail=f"Missing template params: {', '.join(missing)}")

    definition = render_template(template["definition"], params)
    workflow = Workflow(
        user_id=request.state.user_id,
        name=f"{template['name']} ({datetime.now(timezone.utc).strftime('%H:%M:%S')})",
        description=template.get("description"),
        definition=definition,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(workflow)
    db.commit()
    db.refresh(workflow)

    run = WorkflowRun(
        workflow_id=workflow.id,
        user_id=request.state.user_id,
        status="running",
        created_at=datetime.now(timezone.utc),
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    run_workflow_task.delay(str(run.id))
    return run

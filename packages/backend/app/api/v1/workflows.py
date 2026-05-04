"""Workflow API endpoints."""

import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from redis.asyncio import Redis
from sqlalchemy.orm import Session

from app.db.session import get_db, SessionLocal
from app.models.workflow import Workflow
from app.models.workflow_run import WorkflowRun
from app.repositories import WorkflowRepository, WorkflowRunRepository
from app.schemas.workflow import WorkflowCreate, WorkflowResponse, WorkflowRunResponse, WorkflowUpdate
from app.runtime.services.metrics import runtime_metrics
from app.tasks.workflow_tasks import run_workflow_task
from app.core.config import settings

router = APIRouter(prefix="/workflows", tags=["workflows"])


@router.post("", response_model=WorkflowResponse, status_code=status.HTTP_201_CREATED)
def create_workflow(
    payload: WorkflowCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    user_id = request.state.user_id
    workflow = Workflow(
        user_id=user_id,
        name=payload.name,
        description=payload.description,
        definition=payload.definition,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(workflow)
    db.commit()
    db.refresh(workflow)
    return workflow


@router.get("", response_model=list[WorkflowResponse])
def list_workflows(request: Request, db: Session = Depends(get_db)):
    user_id = request.state.user_id
    return WorkflowRepository(db).list_by_user(user_id)


@router.get("/{workflow_id}", response_model=WorkflowResponse)
def get_workflow(workflow_id: uuid.UUID, request: Request, db: Session = Depends(get_db)):
    workflow = WorkflowRepository(db).get_by_id_and_user(workflow_id, request.state.user_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return workflow


@router.patch("/{workflow_id}", response_model=WorkflowResponse)
def update_workflow(
    workflow_id: uuid.UUID,
    payload: WorkflowUpdate,
    request: Request,
    db: Session = Depends(get_db),
):
    repo = WorkflowRepository(db)
    workflow = repo.get_by_id_and_user(workflow_id, request.state.user_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    if payload.name is not None:
        workflow.name = payload.name
    if payload.description is not None:
        workflow.description = payload.description
    if payload.definition is not None:
        workflow.definition = payload.definition
    workflow.updated_at = datetime.now(timezone.utc)

    db.add(workflow)
    db.commit()
    db.refresh(workflow)
    return workflow


@router.delete("/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workflow(workflow_id: uuid.UUID, request: Request, db: Session = Depends(get_db)):
    repo = WorkflowRepository(db)
    workflow = repo.get_by_id_and_user(workflow_id, request.state.user_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    db.query(WorkflowRun).filter(
        WorkflowRun.workflow_id == workflow_id,
        WorkflowRun.user_id == request.state.user_id,
    ).delete(synchronize_session=False)
    db.delete(workflow)
    db.commit()
    return None


@router.post("/{workflow_id}/runs", response_model=WorkflowRunResponse, status_code=status.HTTP_201_CREATED)
def run_workflow(
    workflow_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
):
    workflow = WorkflowRepository(db).get_by_id_and_user(workflow_id, request.state.user_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

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


@router.get("/runs/{run_id}", response_model=WorkflowRunResponse)
def get_run(run_id: uuid.UUID, request: Request, db: Session = Depends(get_db)):
    run = WorkflowRunRepository(db).get_by_id_and_user(run_id, request.state.user_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


async def _run_event_stream(run_id: str, user_id: str):
    def _run_payload(run: WorkflowRun) -> dict:
        return {
            "type": "run",
            "id": str(run.id),
            "workflow_id": str(run.workflow_id),
            "status": run.status,
            "result": run.result,
            "error": run.error,
            "created_at": run.created_at.isoformat() if run.created_at else None,
            "finished_at": run.finished_at.isoformat() if run.finished_at else None,
        }

    db = SessionLocal()
    try:
        run = WorkflowRunRepository(db).get_by_id_and_user(run_id, user_id)
        if not run:
            yield f"data: {json.dumps({'type': 'run', 'status': 'not_found'})}\n\n"
            return
        yield f"data: {json.dumps(_run_payload(run))}\n\n"
        if run.status not in {"running", "pending"}:
            return
    finally:
        db.close()

    redis_client = Redis.from_url(settings.REDIS_URL)
    pubsub = redis_client.pubsub()
    channel = f"workflow_run:{run_id}"

    await pubsub.subscribe(channel)
    runtime_metrics.increment("sse.stream.open.count", tags={"stream": "workflow_run"})
    runtime_metrics.change_gauge("sse.stream.active", 1, tags={"stream": "workflow_run"})
    db = SessionLocal()
    try:
        latest = WorkflowRunRepository(db).get_by_id_and_user(run_id, user_id)
        if latest and latest.status not in {"running", "pending"}:
            yield f"data: {json.dumps(_run_payload(latest))}\n\n"
            return
    finally:
        db.close()

    try:
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue
            data_str = message["data"].decode("utf-8")
            try:
                payload = json.loads(data_str)
            except json.JSONDecodeError:
                payload = {"raw": data_str}
            runtime_metrics.increment("sse.stream.message.count", tags={"stream": "workflow_run"})
            yield f"data: {json.dumps(payload)}\n\n"
            if payload.get("type") == "run":
                status = payload.get("status")
                if status and status not in {"running", "pending"}:
                    break
    finally:
        runtime_metrics.change_gauge("sse.stream.active", -1, tags={"stream": "workflow_run"})
        runtime_metrics.increment("sse.stream.close.count", tags={"stream": "workflow_run"})
        await pubsub.unsubscribe(channel)
        await redis_client.close()


@router.get("/runs/{run_id}/stream")
async def stream_run(run_id: uuid.UUID, request: Request):
    return StreamingResponse(
        _run_event_stream(str(run_id), str(request.state.user_id)),
        media_type="text/event-stream",
    )

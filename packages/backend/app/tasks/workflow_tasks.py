"""Workflow execution Celery tasks."""

from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime

from app.core.celery_app import celery_app
from app.core.config import settings
from app.models.workflow import Workflow
from app.models.workflow_run import WorkflowRun
from app.repositories import DataSourceRepository, WorkflowRepository, WorkflowRunRepository
from app.infra import RedisEventBus
from app.workflow.services.execution import run_workflow, update_workflow_run
from app.sandbox import sandbox_manager
from app.workflow.services.file_service import service_run_workflow_draft, service_run_workflow_from_file
from app.tasks.db import open_task_session


async def _publish(channel: str, payload: dict) -> None:
    event_bus = RedisEventBus(settings.REDIS_URL)
    try:
        await event_bus.publish(channel, json.dumps(payload))
    finally:
        await event_bus.close()


def _publish_run(run: WorkflowRun) -> None:
    channel = f"workflow_run:{run.id}"
    payload = {
        "type": "run",
        "id": str(run.id),
        "workflow_id": str(run.workflow_id),
        "status": run.status,
        "result": run.result,
        "error": run.error,
        "created_at": run.created_at.isoformat() if run.created_at else None,
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
    }
    asyncio.run(_publish(channel, payload))


def _publish_node(run: WorkflowRun, node_id: str, node_status: str, outputs: dict | None = None) -> None:
    channel = f"workflow_run:{run.id}"
    payload = {
        "type": "node",
        "run_id": str(run.id),
        "node_id": node_id,
        "status": node_status,
        "outputs": outputs,
    }
    asyncio.run(_publish(channel, payload))


def _workflow_file_datasources(db, workflow: Workflow, user_id) -> list:
    """Collect file datasources referenced by datasource.read nodes in a workflow definition."""
    definition = workflow.definition or {}
    graph_data = definition.get("root", definition)
    if not isinstance(graph_data, dict):
        return []

    raw_nodes = graph_data.get("nodes")
    if not isinstance(raw_nodes, dict):
        return []

    repo = DataSourceRepository(db)
    seen: set[str] = set()
    datasources = []

    for raw_node in raw_nodes.values():
        if not isinstance(raw_node, dict) or raw_node.get("type") != "datasource.read":
            continue
        params = raw_node.get("params")
        if not isinstance(params, dict):
            continue
        datasource_id = params.get("datasource_id")
        if not datasource_id:
            continue
        try:
            datasource = repo.get_by_id_and_user(str(datasource_id), user_id)
        except Exception:
            continue
        if not datasource or getattr(datasource, "category", None) != "file" or not getattr(datasource, "storage_path", None):
            continue
        key = str(datasource.id)
        if key in seen:
            continue
        seen.add(key)
        datasources.append(datasource)

    return datasources


@celery_app.task(bind=True)
def run_workflow_task(self, run_id: str) -> dict:
    db = open_task_session()
    try:
        run_repo = WorkflowRunRepository(db)
        workflow_repo = WorkflowRepository(db)
        run_lookup_id = uuid.UUID(str(run_id))

        run = run_repo.get(run_lookup_id)
        if not run:
            return {"status": "error", "error": "run not found"}

        workflow = workflow_repo.get(run.workflow_id)
        if not workflow:
            run.status = "failed"
            run.error = "workflow not found"
            run.finished_at = datetime.utcnow()
            db.commit()
            _publish_run(run)
            return {"status": "error", "error": "workflow not found"}

        _publish_run(run)
        sandbox_session_key = str(run.session_id or run.id)
        sandbox = asyncio.run(sandbox_manager.get_or_create_sandbox(sandbox_session_key))
        file_datasources = _workflow_file_datasources(db, workflow, run.user_id)
        if file_datasources:
            asyncio.run(sandbox_manager.sync_datasource_files(sandbox_session_key, file_datasources))
        result = run_workflow(
            db,
            workflow,
            run.user_id,
            sandbox=sandbox,
            on_node_start=lambda node_id, node_run, _: _publish_node(run, node_id, node_run.status),
            on_node_end=lambda node_id, node_run, _: _publish_node(
                run, node_id, node_run.status, node_run.outputs
            ),
        )
        update_workflow_run(db, run, result)
        _publish_run(run)
        return {"status": "finished", "run_id": str(run.id)}
    except Exception as exc:
        try:
            run_lookup_id = uuid.UUID(str(run_id))
        except ValueError:
            run_lookup_id = None
        run = WorkflowRunRepository(db).get(run_lookup_id) if run_lookup_id else None
        if run:
            run.status = "failed"
            run.error = str(exc)
            run.finished_at = datetime.utcnow()
            db.commit()
            _publish_run(run)
        return {"status": "error", "error": str(exc)}
    finally:
        db.close()


@celery_app.task(bind=True)
def run_workflow_file_task(
    self,
    user_id: str,
    session_id: str,
    path: str,
    turn_id: str | None = None,
    draft_id: str | None = None,
    run_id: str | None = None,
) -> dict:
    db = open_task_session()
    try:
        result = asyncio.run(
            service_run_workflow_from_file(
                db,
                user_id,
                session_id,
                path,
                turn_id=turn_id,
                draft_id=draft_id,
                run_id=run_id,
            )
        )
        return {"status": "finished", "result": result}
    except Exception as exc:
        return {"status": "error", "error": str(exc)}
    finally:
        db.close()


@celery_app.task(bind=True)
def run_workflow_draft_task(
    self,
    user_id: str,
    session_id: str,
    draft_id: str,
    turn_id: str | None = None,
    run_id: str | None = None,
) -> dict:
    db = open_task_session()
    try:
        result = asyncio.run(
            service_run_workflow_draft(
                db,
                user_id,
                session_id,
                draft_id,
                turn_id=turn_id,
                run_id=run_id,
            )
        )
        return {"status": "finished", "result": result}
    except Exception as exc:
        return {"status": "error", "error": str(exc)}
    finally:
        db.close()

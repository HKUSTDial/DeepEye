"""Workflow execution service."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.workflow import Workflow
from app.models.workflow_run import WorkflowRun
from app.workflow.services.engine import build_engine
from deepeye.workflows.models import Graph, Workflow as CoreWorkflow


def run_workflow(
    db: Session,
    workflow: Workflow,
    user_id,
    *,
    sandbox=None,
    on_node_start: callable | None = None,
    on_node_end: callable | None = None,
) -> dict[str, Any]:
    core_workflow = _to_core_workflow(workflow)
    engine = build_engine(db, user_id, sandbox=sandbox)
    context = engine.run(core_workflow, on_node_start=on_node_start, on_node_end=on_node_end)
    return {
        "status": context.status,
        "runs": {
            node_id: {
                "status": run.status,
                "inputs": run.inputs,
                "outputs": run.outputs,
                "error": run.error,
            }
            for node_id, run in context.runs.items()
        },
    }


def update_workflow_run(db: Session, run: WorkflowRun, result: dict[str, Any]) -> WorkflowRun:
    run.status = result.get("status", "failed")
    run.result = result
    run.finished_at = datetime.now(timezone.utc)
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def _to_core_workflow(workflow: Workflow) -> CoreWorkflow:
    definition = workflow.definition or {}
    graph_data = definition.get("root", definition)
    graph = Graph.model_validate(graph_data)
    return CoreWorkflow(
        id=str(workflow.id),
        name=workflow.name,
        description=workflow.description,
        root=graph,
    )

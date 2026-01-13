from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
import asyncio

from app.infra import RedisEventBus
from app.sandbox import sandbox_manager
from app.core.config import settings
from app.schemas import AgentEvent, AgentEventType
from app.services.workflow_engine import build_engine
from pydantic import ValidationError
from deepeye.workflows.models import Graph, Workflow as CoreWorkflow
from deepeye.workflows.runtime import ExecutionContext
from deepeye.workflows.validation import WorkflowValidationError


async def service_run_workflow_from_file(
    db,
    user_id,
    session_id: str,
    path: str,
) -> dict[str, Any]:
    channel = f"session:{session_id}"
    event_bus = RedisEventBus(settings.REDIS_URL)

    def _timestamp() -> str:
        return datetime.now(timezone.utc).isoformat()

    async def _publish(event_type: AgentEventType, data: dict | None = None):
        event = AgentEvent(type=event_type, data=data or {})
        await event_bus.publish(channel, event.model_dump_json())

    async def _publish_workflow_event(phase: str, payload: dict | None = None):
        await _publish(
            AgentEventType.WORKFLOW_EVENT,
            {
                "session_id": session_id,
                "file_path": path,
                "phase": phase,
                "payload": payload or {},
            },
        )

    try:
        await _publish_workflow_event("run_start", {"path": path, "started_at": _timestamp()})

        # Use get_or_create to ensure container exists
        sandbox = await sandbox_manager.get_or_create_sandbox(session_id)
        if not sandbox:
            raise ValueError("failed to get or create sandbox")

        result = await sandbox.exec_command(f"cat {path}")
        if result.exit_code != 0:
            raise ValueError(result.stderr or "failed to read workflow file")

        definition = json.loads(result.stdout)
        graph_data = definition.get("root", definition)
        graph = Graph.model_validate(graph_data)
        core_workflow = CoreWorkflow(id=f"file:{path}", root=graph)

        engine = build_engine(db, user_id, sandbox=sandbox)
        loop = asyncio.get_running_loop()

        def _on_node_start(node_id, node_run, _):
            data = {"node_id": node_id, "status": node_run.status}
            loop.create_task(_publish_workflow_event("node_status", data))

        def _on_node_end(node_id, node_run, _):
            data = {"node_id": node_id, "status": node_run.status, "outputs": node_run.outputs}
            loop.create_task(_publish_workflow_event("node_status", data))

        context = engine.run(core_workflow, on_node_start=_on_node_start, on_node_end=_on_node_end)
        outputs = _collect_final_outputs(graph, context)
        await _publish_workflow_event(
            "run_end",
            {"status": context.status, "finished_at": _timestamp(), "outputs": outputs},
        )
        return {"status": context.status, "outputs": outputs}
    except WorkflowValidationError as exc:
        issues = [
            {
                "code": issue.code,
                "message": issue.message,
                "location": issue.location,
            }
            for issue in exc.issues
        ]
        error = "Workflow validation failed"
        await _publish_workflow_event(
            "error",
            {
                "message": error,
                "validation_errors": issues,
            },
        )
        await _publish_workflow_event(
            "run_end",
            {
                "status": "failed",
                "error": error,
                "validation_errors": issues,
                "finished_at": _timestamp(),
            },
        )
        return {"status": "failed", "error": error, "validation_errors": issues}
    except ValidationError as exc:
        error = "Workflow definition is invalid"
        await _publish_workflow_event(
            "error",
            {
                "message": error,
                "details": exc.errors(),
            },
        )
        await _publish_workflow_event(
            "run_end",
            {
                "status": "failed",
                "error": error,
                "details": exc.errors(),
                "finished_at": _timestamp(),
            },
        )
        return {"status": "failed", "error": error, "details": exc.errors()}
    except Exception as exc:
        await _publish_workflow_event(
            "error",
            {
                "message": str(exc),
            },
        )
        await _publish_workflow_event(
            "run_end",
            {"status": "failed", "error": str(exc), "finished_at": _timestamp()},
        )
        return {"status": "failed", "error": str(exc)}
    finally:
        await event_bus.close()


def _collect_final_outputs(graph: Graph, context: ExecutionContext) -> dict[str, Any]:
    outputs: dict[str, Any] = {}
    for node_id in graph.nodes.keys():
        run = context.runs.get(node_id)
        if not run or not run.outputs:
            continue
        non_empty = {key: value for key, value in run.outputs.items() if value not in (None, "", [], {})}
        if non_empty:
            outputs[node_id] = non_empty
    return outputs

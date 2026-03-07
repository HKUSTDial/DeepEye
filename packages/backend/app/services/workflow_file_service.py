from __future__ import annotations

import asyncio
import json
import threading
from datetime import datetime, timezone
from typing import Any, Callable

from app.infra import RedisEventBus
from app.sandbox import sandbox_manager
from app.core.config import settings
from app.schemas import AgentEvent, AgentEventType
from app.services.workflow_engine import build_engine
from app.services.workflow_events import build_workflow_event_data, extract_workflow_artifacts
from pydantic import ValidationError
from deepeye.workflows.models import Graph, Workflow as CoreWorkflow
from deepeye.workflows.runtime import ExecutionContext
from deepeye.workflows.validation import WorkflowValidationError

# 全局字典：存储 session_id -> 进度发布函数
_progress_publishers: dict[str, Callable[[str], None]] = {}
# 全局字典：存储 workflow_id -> session_id 的映射
_workflow_to_session: dict[str, str] = {}


def get_progress_publisher(session_id: str) -> Callable[[str], None] | None:
    """获取指定 session 的进度发布函数"""
    return _progress_publishers.get(session_id)


def get_progress_publisher_by_workflow_id(workflow_id: str) -> Callable[[str], None] | None:
    """通过 workflow_id 获取进度发布函数"""
    session_id = _workflow_to_session.get(workflow_id)
    if session_id:
        return _progress_publishers.get(session_id)
    return None


def get_session_id_by_workflow_id(workflow_id: str) -> str | None:
    """通过 workflow_id 获取 session_id（用于会话隔离存储）。"""
    return _workflow_to_session.get(workflow_id)


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
            build_workflow_event_data(session_id, phase, payload, file_path=path),
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
        
        # 注册 workflow_id -> session_id 映射
        _workflow_to_session[core_workflow.id] = session_id

        engine = build_engine(db, user_id, sandbox=sandbox, session_id=session_id)
        loop = asyncio.get_running_loop()
        result_holder: list = []  # [ExecutionContext] or [Exception]

        # 进度回调：从 worker 线程通过主循环发送 TOKEN，保证中途过程能实时展示
        def _publish_progress_message(message: str):
            line = message if message.endswith("\n") else message + "\n"
            payload = {"content": line, "source": "workflow"}

            def _schedule():
                asyncio.create_task(_publish(AgentEventType.TOKEN, payload))

            loop.call_soon_threadsafe(_schedule)

        _progress_publishers[session_id] = _publish_progress_message

        def _on_node_start(node_id, node_run, _):
            data = {"node_id": node_id, "status": node_run.status}

            def _schedule():
                asyncio.create_task(_publish_workflow_event("node_status", data))

            loop.call_soon_threadsafe(_schedule)

        def _on_node_end(node_id, node_run, _):
            data = {"node_id": node_id, "status": node_run.status, "outputs": node_run.outputs}

            def _schedule():
                asyncio.create_task(_publish_workflow_event("node_status", data))

            loop.call_soon_threadsafe(_schedule)

        def _run_workflow_sync():
            try:
                ctx = engine.run(
                    core_workflow,
                    on_node_start=_on_node_start,
                    on_node_end=_on_node_end,
                )
                result_holder.append(ctx)
            except Exception as e:
                result_holder.append(e)

        thread = threading.Thread(target=_run_workflow_sync)
        thread.start()
        while not result_holder:
            await asyncio.sleep(0.05)

        if isinstance(result_holder[0], Exception):
            raise result_holder[0]
        context = result_holder[0]
        outputs = _collect_final_outputs(graph, context)
        artifacts = extract_workflow_artifacts(outputs)
        await _publish_workflow_event(
            "run_end",
            {
                "status": context.status,
                "finished_at": _timestamp(),
                "outputs": outputs,
                "artifacts": artifacts,
            },
        )
        return {"status": context.status, "outputs": outputs, "artifacts": artifacts}
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
        # 清理进度发布函数和映射
        _progress_publishers.pop(session_id, None)
        # 清理所有指向此 session_id 的 workflow_id 映射
        workflows_to_remove = [wid for wid, sid in _workflow_to_session.items() if sid == session_id]
        for wid in workflows_to_remove:
            _workflow_to_session.pop(wid, None)
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

from __future__ import annotations

import asyncio
import json
import shlex
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Callable

from app.infra import RedisEventBus
from app.sandbox import sandbox_manager
from app.core.config import settings
from app.schemas import AgentEvent, AgentEventType
from app.repositories import WorkflowDraftRepository, WorkflowRunRepository
from app.services.workflow_engine import build_engine
from app.services.workflow_datasets import compact_node_outputs, compact_workflow_outputs
from app.services.workflow_events import build_workflow_event_data, extract_workflow_artifacts
from app.services.workflow_tracking_service import (
    create_tracked_workflow_run,
    finalize_tracked_workflow_run,
    get_chat_turn,
    get_latest_active_turn,
    replace_workflow_artifacts,
    upsert_workflow_draft,
)
from app.services.workflow_targets import resolve_workflow_target
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


def _as_uuid(value: str | uuid.UUID | None) -> uuid.UUID | None:
    if value is None or isinstance(value, uuid.UUID):
        return value
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError):
        return None


async def load_workflow_definition_from_file(session_id: str, path: str) -> dict[str, Any]:
    sandbox = await sandbox_manager.get_or_create_sandbox(session_id)
    if not sandbox:
        raise ValueError("failed to get or create sandbox")

    result = await sandbox.exec_command(f"cat {path}")
    if result.exit_code != 0:
        raise ValueError(result.stderr or "failed to read workflow file")

    return json.loads(result.stdout)


async def write_workflow_definition_to_file(session_id: str, path: str, definition: dict[str, Any]) -> None:
    sandbox = await sandbox_manager.get_or_create_sandbox(session_id)
    if not sandbox:
        raise ValueError("failed to get or create sandbox")

    await sandbox.exec_command("mkdir -p /workspace/workflow")
    payload = json.dumps(definition, ensure_ascii=False, indent=2)
    quoted_path = shlex.quote(path)
    result = await sandbox.exec_command(f"cat > {quoted_path} << 'EOF'\n{payload}\nEOF")
    if result.exit_code != 0:
        raise ValueError(result.stderr or "failed to write workflow file")


def prepare_tracked_workflow_file_run(
    db,
    *,
    user_id,
    session_id: str,
    path: str,
    definition: dict[str, Any],
    turn_id: str | None = None,
    draft_id: str | None = None,
    run_id: str | None = None,
):
    return prepare_tracked_workflow_run(
        db,
        user_id=user_id,
        session_id=session_id,
        path=path,
        definition=definition,
        turn_id=turn_id,
        draft_id=draft_id,
        run_id=run_id,
        draft_source="workflow_file",
        run_source="workflow_file",
    )


def prepare_tracked_workflow_run(
    db,
    *,
    user_id,
    session_id: str,
    definition: dict[str, Any],
    path: str | None = None,
    turn_id: str | None = None,
    draft_id: str | None = None,
    run_id: str | None = None,
    draft_source: str | None = None,
    run_source: str = "workflow_file",
):
    tracked_turn = get_chat_turn(db, turn_id) if turn_id else get_latest_active_turn(db, session_id)

    draft_repo = WorkflowDraftRepository(db)
    tracked_draft = draft_repo.get(_as_uuid(draft_id)) if draft_id else None
    if tracked_draft:
        tracked_draft.definition = definition
        tracked_draft.file_path = path
        tracked_draft.turn_id = tracked_turn.id if tracked_turn else None
        tracked_draft.status = "draft"
        if draft_source:
            tracked_draft.source = draft_source
        tracked_draft.version = max(1, tracked_draft.version)
        tracked_draft = draft_repo.save(tracked_draft)
    else:
        tracked_draft = upsert_workflow_draft(
            db,
            session_id=session_id,
            user_id=user_id,
            definition=definition,
            file_path=path,
            turn_id=tracked_turn.id if tracked_turn else None,
            source=draft_source or run_source,
        )

    run_repo = WorkflowRunRepository(db)
    tracked_run = run_repo.get(_as_uuid(run_id)) if run_id else None
    if tracked_run:
        tracked_run.session_id = tracked_draft.session_id
        tracked_run.turn_id = tracked_turn.id if tracked_turn else None
        tracked_run.draft_id = tracked_draft.id if tracked_draft else None
        tracked_run.file_path = path
        tracked_run.source = run_source
        tracked_run.status = "running"
        tracked_run.result = None
        tracked_run.artifacts = None
        tracked_run.error = None
        tracked_run.finished_at = None
        tracked_run = run_repo.save(tracked_run)
    else:
        tracked_run = create_tracked_workflow_run(
            db,
            user_id=user_id,
            session_id=session_id,
            turn_id=tracked_turn.id if tracked_turn else None,
            draft_id=tracked_draft.id if tracked_draft else None,
            file_path=path,
            source=run_source,
        )

    return tracked_turn, tracked_draft, tracked_run


def prepare_tracked_workflow_draft_run(
    db,
    *,
    user_id,
    session_id: str,
    draft_id: str,
    turn_id: str | None = None,
    run_id: str | None = None,
):
    tracked_draft, path = resolve_workflow_target(
        db,
        session_id,
        draft_id=draft_id,
    )
    if not tracked_draft or not isinstance(tracked_draft.definition, dict):
        raise ValueError("Workflow draft not found.")
    tracked_turn, tracked_draft, tracked_run = prepare_tracked_workflow_run(
        db,
        user_id=user_id,
        session_id=session_id,
        definition=tracked_draft.definition,
        path=path,
        turn_id=turn_id,
        draft_id=str(tracked_draft.id),
        run_id=run_id,
        draft_source=None,
        run_source="workflow_draft",
    )
    return tracked_turn, tracked_draft, tracked_run, path


def _summarize_failed_context(graph: Graph, context: ExecutionContext) -> tuple[str, list[dict[str, Any]]]:
    failed_nodes: list[dict[str, Any]] = []
    for node_id, node_run in context.runs.items():
        if node_run.status != "failed":
            continue
        node = graph.nodes.get(node_id)
        failed_nodes.append(
            {
                "node_id": node_id,
                "node_type": node.type if node else None,
                "message": node_run.error or "Node execution failed.",
            }
        )

    if not failed_nodes:
        return "Workflow execution failed.", []

    first = failed_nodes[0]
    node_label = first.get("node_id") or "unknown"
    node_type = first.get("node_type")
    message = first.get("message") or "Node execution failed."
    if node_type:
        summary = f"Workflow execution failed at node {node_label} ({node_type}): {message}"
    else:
        summary = f"Workflow execution failed at node {node_label}: {message}"
    return summary, failed_nodes


async def service_run_workflow_definition(
    db,
    user_id,
    session_id: str,
    definition: dict[str, Any],
    *,
    path: str | None = None,
    workflow_ref: str | None = None,
    turn_id: str | None = None,
    draft_id: str | None = None,
    run_id: str | None = None,
    draft_source: str | None = None,
    run_source: str = "workflow_file",
) -> dict[str, Any]:
    channel = f"session:{session_id}"
    event_bus = RedisEventBus(settings.REDIS_URL)
    tracked_turn = None
    tracked_draft = None
    tracked_run = None
    workflow_path = path

    def _timestamp() -> str:
        return datetime.now(timezone.utc).isoformat()

    async def _publish(event_type: AgentEventType, data: dict | None = None):
        event = AgentEvent(type=event_type, data=data or {})
        await event_bus.publish(channel, event.model_dump_json())

    async def _publish_workflow_event(phase: str, payload: dict | None = None):
        await _publish(
            AgentEventType.WORKFLOW_EVENT,
            build_workflow_event_data(
                session_id,
                phase,
                payload,
                file_path=workflow_path,
                turn_id=str(tracked_turn.id) if tracked_turn else turn_id,
                draft_id=str(tracked_draft.id) if tracked_draft else None,
                run_id=str(tracked_run.id) if tracked_run else None,
            ),
        )

    try:
        graph_data = definition.get("root", definition)
        graph = Graph.model_validate(graph_data)
        tracked_turn, tracked_draft, tracked_run = prepare_tracked_workflow_run(
            db,
            user_id=user_id,
            session_id=session_id,
            definition=definition,
            path=workflow_path,
            turn_id=turn_id,
            draft_id=draft_id,
            run_id=run_id,
            draft_source=draft_source,
            run_source=run_source,
        )
        workflow_path = workflow_path or (tracked_draft.file_path if tracked_draft else None)
        workflow_identity = workflow_ref
        if not workflow_identity:
            if tracked_draft:
                workflow_identity = f"draft:{tracked_draft.id}"
            elif workflow_path:
                workflow_identity = f"file:{workflow_path}"
            else:
                workflow_identity = f"session:{session_id}"
        core_workflow = CoreWorkflow(id=workflow_identity, root=graph)

        sandbox = await sandbox_manager.get_or_create_sandbox(session_id)
        if not sandbox:
            raise ValueError("failed to get or create sandbox")

        await _publish_workflow_event("run_start", {"started_at": _timestamp()})

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
            data = {
                "node_id": node_id,
                "status": node_run.status,
                "outputs": compact_node_outputs(node_run.outputs),
            }

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
        if context.status != "success":
            error, details = _summarize_failed_context(graph, context)
            if tracked_run:
                finalize_tracked_workflow_run(
                    db,
                    tracked_run,
                    status="failed",
                    result={"status": "failed", "details": details, "outputs": {}},
                    error=error,
                    artifacts=[],
                )
            await _publish_workflow_event(
                "error",
                {
                    "message": error,
                    "details": details,
                },
            )
            await _publish_workflow_event(
                "run_end",
                {
                    "status": "failed",
                    "error": error,
                    "details": details,
                    "finished_at": _timestamp(),
                },
            )
            return {
                "status": "failed",
                "error": error,
                "details": details,
                "turn_id": str(tracked_turn.id) if tracked_turn else turn_id,
                "draft_id": str(tracked_draft.id) if tracked_draft else None,
                "run_id": str(tracked_run.id) if tracked_run else None,
            }
        outputs = _collect_final_outputs(graph, context)
        artifacts = extract_workflow_artifacts(outputs)
        compact_outputs = compact_workflow_outputs(outputs)
        if tracked_run:
            replace_workflow_artifacts(db, tracked_run, artifacts)
            finalize_tracked_workflow_run(
                db,
                tracked_run,
                status=context.status,
                result={"status": context.status, "outputs": compact_outputs, "artifacts": artifacts},
                artifacts=artifacts,
            )
        await _publish_workflow_event(
            "run_end",
            {
                "status": context.status,
                "finished_at": _timestamp(),
                "outputs": compact_outputs,
                "artifacts": artifacts,
            },
        )
        return {
            "status": context.status,
            "outputs": compact_outputs,
            "artifacts": artifacts,
            "turn_id": str(tracked_turn.id) if tracked_turn else turn_id,
            "draft_id": str(tracked_draft.id) if tracked_draft else None,
            "run_id": str(tracked_run.id) if tracked_run else None,
        }
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
        if tracked_run:
            finalize_tracked_workflow_run(
                db,
                tracked_run,
                status="failed",
                result={"status": "failed", "validation_errors": issues},
                error=error,
                artifacts=[],
            )
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
        return {
            "status": "failed",
            "error": error,
            "validation_errors": issues,
            "turn_id": str(tracked_turn.id) if tracked_turn else turn_id,
            "draft_id": str(tracked_draft.id) if tracked_draft else None,
            "run_id": str(tracked_run.id) if tracked_run else None,
        }
    except ValidationError as exc:
        error = "Workflow definition is invalid"
        if tracked_run:
            finalize_tracked_workflow_run(
                db,
                tracked_run,
                status="failed",
                result={"status": "failed", "details": exc.errors()},
                error=error,
                artifacts=[],
            )
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
        return {
            "status": "failed",
            "error": error,
            "details": exc.errors(),
            "turn_id": str(tracked_turn.id) if tracked_turn else turn_id,
            "draft_id": str(tracked_draft.id) if tracked_draft else None,
            "run_id": str(tracked_run.id) if tracked_run else None,
        }
    except Exception as exc:
        if tracked_run:
            finalize_tracked_workflow_run(
                db,
                tracked_run,
                status="failed",
                result={"status": "failed", "error": str(exc)},
                error=str(exc),
                artifacts=[],
            )
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
        return {
            "status": "failed",
            "error": str(exc),
            "turn_id": str(tracked_turn.id) if tracked_turn else turn_id,
            "draft_id": str(tracked_draft.id) if tracked_draft else None,
            "run_id": str(tracked_run.id) if tracked_run else None,
        }
    finally:
        # 清理进度发布函数和映射
        _progress_publishers.pop(session_id, None)
        # 清理所有指向此 session_id 的 workflow_id 映射
        workflows_to_remove = [wid for wid, sid in _workflow_to_session.items() if sid == session_id]
        for wid in workflows_to_remove:
            _workflow_to_session.pop(wid, None)
        await event_bus.close()


async def service_run_workflow_from_file(
    db,
    user_id,
    session_id: str,
    path: str,
    *,
    turn_id: str | None = None,
    draft_id: str | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    definition = await load_workflow_definition_from_file(session_id, path)
    return await service_run_workflow_definition(
        db,
        user_id,
        session_id,
        definition,
        path=path,
        workflow_ref=f"file:{path}",
        turn_id=turn_id,
        draft_id=draft_id,
        run_id=run_id,
        draft_source="workflow_file",
        run_source="workflow_file",
    )


async def service_run_workflow_draft(
    db,
    user_id,
    session_id: str,
    draft_id: str,
    *,
    turn_id: str | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    tracked_draft, path = resolve_workflow_target(
        db,
        session_id,
        draft_id=draft_id,
    )
    if not tracked_draft or not isinstance(tracked_draft.definition, dict):
        raise ValueError("Workflow draft not found.")
    await write_workflow_definition_to_file(session_id, path, tracked_draft.definition)
    return await service_run_workflow_definition(
        db,
        user_id,
        session_id,
        tracked_draft.definition,
        path=path,
        workflow_ref=f"draft:{tracked_draft.id}",
        turn_id=turn_id,
        draft_id=str(tracked_draft.id),
        run_id=run_id,
        draft_source=None,
        run_source="workflow_draft",
    )


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

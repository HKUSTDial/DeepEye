from __future__ import annotations

import asyncio
import json
import shlex
from typing import Any

from app.infra import RedisEventBus
from app.core.config import settings
from app.sandbox import sandbox_manager
from app.schemas import AgentEvent, AgentEventType
from app.services.workflow_datasets import compact_node_outputs, compact_workflow_outputs
from app.services.workflow_engine import build_engine
from app.services.workflow_run_preparation import (
    prepare_tracked_workflow_draft_run as prepare_tracked_workflow_draft_run,
    prepare_tracked_workflow_file_run as prepare_tracked_workflow_file_run,
    prepare_tracked_workflow_run,
)
from app.services.workflow_run_result import (
    build_tracking_refs,
    build_workflow_identity,
    collect_final_outputs,
    finalize_failed_run,
    finalize_successful_run,
    summarize_failed_context,
    timestamp_utc,
)
from app.services.workflow_runtime_registry import (
    clear_workflow_runtime_state,
    get_progress_publisher as get_progress_publisher,
    get_progress_publisher_by_workflow_id as get_progress_publisher_by_workflow_id,
    get_session_id_by_workflow_id as get_session_id_by_workflow_id,
    register_workflow_progress,
)
from app.services.workflow_targets import resolve_workflow_target
from app.workflow.events import build_workflow_event_data, extract_workflow_artifacts
from pydantic import ValidationError
from deepeye.workflows.models import Graph, Workflow as CoreWorkflow
from deepeye.workflows.validation import WorkflowValidationError

_summarize_failed_context = summarize_failed_context


async def load_workflow_definition_from_file(session_id: str, path: str) -> dict[str, Any]:
    sandbox = await sandbox_manager.get_or_create_sandbox(session_id)
    if not sandbox:
        raise ValueError("failed to get or create sandbox")

    result = await sandbox.exec_command(f"cat {shlex.quote(path)}")
    if result.exit_code != 0:
        raise ValueError(result.stderr or "failed to read workflow file")

    return json.loads(result.stdout)


async def write_workflow_definition_to_file(session_id: str, path: str, definition: dict[str, Any]) -> None:
    sandbox = await sandbox_manager.get_or_create_sandbox(session_id)
    if not sandbox:
        raise ValueError("failed to get or create sandbox")

    payload = json.dumps(definition, ensure_ascii=False, indent=2)
    await sandbox.write_text_file(path, payload)


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

    async def _publish(event_type: AgentEventType, data: dict | None = None):
        event = AgentEvent(type=event_type, data=data or {})
        await event_bus.publish(channel, event.model_dump_json())

    def _tracking_refs() -> dict[str, str | None]:
        return build_tracking_refs(tracked_turn, tracked_draft, tracked_run, turn_id)

    async def _publish_workflow_event(phase: str, payload: dict | None = None):
        await _publish(
            AgentEventType.WORKFLOW_EVENT,
            build_workflow_event_data(
                session_id,
                phase,
                payload,
                file_path=workflow_path,
                **_tracking_refs(),
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
        workflow_identity = build_workflow_identity(
            session_id,
            workflow_ref,
            tracked_draft,
            workflow_path,
        )
        core_workflow = CoreWorkflow(id=workflow_identity, root=graph)

        sandbox = await sandbox_manager.get_or_create_sandbox(session_id)
        if not sandbox:
            raise ValueError("failed to get or create sandbox")

        await _publish_workflow_event("run_start", {"started_at": timestamp_utc()})

        engine = build_engine(db, user_id, sandbox=sandbox, session_id=session_id)
        loop = asyncio.get_running_loop()

        # 进度回调：从 worker 线程通过主循环发送 TOKEN，保证中途过程能实时展示
        def _publish_progress_message(message: str):
            line = message if message.endswith("\n") else message + "\n"
            payload = {"content": line, "source": "workflow"}

            def _schedule():
                asyncio.create_task(_publish(AgentEventType.TOKEN, payload))

            loop.call_soon_threadsafe(_schedule)

        register_workflow_progress(session_id, core_workflow.id, _publish_progress_message)

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
            return engine.run(
                core_workflow,
                on_node_start=_on_node_start,
                on_node_end=_on_node_end,
            )

        context = await asyncio.to_thread(_run_workflow_sync)
        if context.status != "success":
            error, details = summarize_failed_context(graph, context)
            await finalize_failed_run(
                db,
                tracked_run,
                _publish_workflow_event,
                error=error,
                result={"status": "failed", "details": details, "outputs": {}},
                error_payload={
                    "message": error,
                    "details": details,
                },
                run_end_payload={
                    "status": "failed",
                    "error": error,
                    "details": details,
                    "finished_at": timestamp_utc(),
                },
            )
            return {
                "status": "failed",
                "error": error,
                "details": details,
                **_tracking_refs(),
            }
        outputs = collect_final_outputs(graph, context)
        artifacts = extract_workflow_artifacts(outputs)
        compact_outputs = compact_workflow_outputs(outputs)
        await finalize_successful_run(
            db,
            tracked_run,
            _publish_workflow_event,
            status=context.status,
            compact_outputs=compact_outputs,
            artifacts=artifacts,
        )
        return {
            "status": context.status,
            "outputs": compact_outputs,
            "artifacts": artifacts,
            **_tracking_refs(),
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
        await finalize_failed_run(
            db,
            tracked_run,
            _publish_workflow_event,
            error=error,
            result={"status": "failed", "validation_errors": issues},
            error_payload={
                "message": error,
                "validation_errors": issues,
            },
            run_end_payload={
                "status": "failed",
                "error": error,
                "validation_errors": issues,
                "finished_at": timestamp_utc(),
            },
        )
        return {
            "status": "failed",
            "error": error,
            "validation_errors": issues,
            **_tracking_refs(),
        }
    except ValidationError as exc:
        error = "Workflow definition is invalid"
        details = exc.errors()
        await finalize_failed_run(
            db,
            tracked_run,
            _publish_workflow_event,
            error=error,
            result={"status": "failed", "details": details},
            error_payload={
                "message": error,
                "details": details,
            },
            run_end_payload={
                "status": "failed",
                "error": error,
                "details": details,
                "finished_at": timestamp_utc(),
            },
        )
        return {
            "status": "failed",
            "error": error,
            "details": details,
            **_tracking_refs(),
        }
    except Exception as exc:
        error = str(exc)
        await finalize_failed_run(
            db,
            tracked_run,
            _publish_workflow_event,
            error=error,
            result={"status": "failed", "error": error},
            error_payload={
                "message": error,
            },
            run_end_payload={"status": "failed", "error": error, "finished_at": timestamp_utc()},
        )
        return {
            "status": "failed",
            "error": error,
            **_tracking_refs(),
        }
    finally:
        clear_workflow_runtime_state(session_id)
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
    tracked_draft, path = resolve_workflow_target(db, session_id, draft_id=draft_id)
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

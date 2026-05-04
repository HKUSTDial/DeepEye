"""Callback for Agent events: streaming + message persistence."""

import ast
import asyncio
import json
import json5
from typing import Any, Literal

from langchain_core.callbacks import AsyncCallbackHandler

from app.infra import EventBus
from app.repositories import MessageRepository
from app.schemas import AgentEvent, AgentEventType, AssistantMessage, Message, ToolStep
from app.workflow.events import build_workflow_event_data
from app.workflow.services.targets import normalize_workflow_path, save_workflow_draft
from app.tasks.db import open_task_session
from deepeye.utils.logger import logger

_WORKFLOW_TRACE_TOOL_NAMES = {
    "create_workflow",
    "create_workflow_and_run",
    "read_workflow",
    "update_workflow",
    "run_workflow",
    "workflow_agent",
}


def _to_single_object(payload: str | dict | Any) -> dict | None:
    """Parse payload to dict. Handles dict, str (JSON/JSON5/Python repr), or other types."""
    if isinstance(payload, dict):
        return payload
    if not isinstance(payload, str):
        # LangChain sometimes passes non-string types (e.g., dict objects directly)
        # Try to handle them gracefully
        if hasattr(payload, '__dict__'):
            logger.debug("[_to_single_object] converting object with __dict__ to dict")
            return vars(payload)
        logger.warning(f"[_to_single_object] unexpected payload type: {type(payload)}, attempting str conversion")
        try:
            payload = str(payload)
        except Exception:
            return None
    
    # Try JSON/JSON5 first
    try:
        return json5.loads(payload)
    except Exception as e1:
        logger.debug(f"[_to_single_object] json5 parse failed: {str(e1)[:100]}")
        try:
            return json.loads(payload)
        except Exception:
            # Fallback for Python-style dict strings (single quotes)
            try:
                val = ast.literal_eval(payload)
                if isinstance(val, dict):
                    return val
            except Exception:
                pass
            logger.warning(f"[_to_single_object] all parse methods failed for payload length: {len(payload)}, preview: {payload[:300]}")
            return None


def _extract_workflow_definition(payload: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(payload, dict):
        return None
    workflow = payload.get("workflow") or payload.get("definition")
    return workflow if isinstance(workflow, dict) else None


def _extract_node_types(workflow: dict[str, Any] | None) -> list[str]:
    if not isinstance(workflow, dict):
        return []
    root = workflow.get("root") if isinstance(workflow.get("root"), dict) else workflow
    if not isinstance(root, dict):
        return []
    nodes = root.get("nodes") or []
    if isinstance(nodes, dict):
        iterable = nodes.values()
    elif isinstance(nodes, list):
        iterable = nodes
    else:
        return []
    node_types: list[str] = []
    for node in iterable:
        if not isinstance(node, dict):
            continue
        node_type = node.get("type")
        if isinstance(node_type, str) and node_type:
            node_types.append(node_type)
    return node_types


def _truncate_for_log(value: str | None, *, limit: int = 240) -> str | None:
    if value is None or len(value) <= limit:
        return value
    return f"{value[:limit]}..."


def _workflow_tool_trace_summary(
    *,
    stage: str,
    source: str,
    tool_name: str,
    session_id: str,
    turn_id: str | None,
    payload: dict[str, Any] | None,
) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "stage": stage,
        "source": source,
        "tool": tool_name,
        "session_id": session_id,
        "turn_id": turn_id,
    }
    if not isinstance(payload, dict):
        return summary

    if stage == "start":
        workflow = _extract_workflow_definition(payload)
        summary.update(
            {
                "draft_id": payload.get("draft_id"),
                "name": payload.get("name"),
                "file_path": payload.get("file_path"),
                "node_types": _extract_node_types(workflow),
            }
        )
        return summary

    run_payload = payload.get("run") if isinstance(payload.get("run"), dict) else payload
    workflow = _extract_workflow_definition(payload)
    validation_errors = run_payload.get("validation_errors")
    details = run_payload.get("details")
    artifacts = run_payload.get("artifacts")
    summary.update(
        {
            "status": run_payload.get("status"),
            "draft_id": payload.get("draft_id") or run_payload.get("draft_id"),
            "run_id": run_payload.get("run_id"),
            "repairable": run_payload.get("repairable"),
            "error_type": run_payload.get("error_type"),
            "error_summary": _truncate_for_log(run_payload.get("error_summary")),
            "error": _truncate_for_log(run_payload.get("error")),
            "validation_error_count": len(validation_errors) if isinstance(validation_errors, list) else 0,
            "details_count": len(details) if isinstance(details, list) else 0,
            "issues": run_payload.get("issues")[:3] if isinstance(run_payload.get("issues"), list) else [],
            "artifact_kinds": [
                artifact.get("kind")
                for artifact in artifacts
                if isinstance(artifact, dict) and isinstance(artifact.get("kind"), str)
            ] if isinstance(artifacts, list) else [],
            "node_types": _extract_node_types(workflow),
            "final_answer_present": isinstance(payload.get("final_answer"), str) and bool(payload.get("final_answer")),
        }
    )
    return summary


def _log_workflow_tool_trace(summary: dict[str, Any]) -> None:
    message = json.dumps(summary, ensure_ascii=False, sort_keys=True)
    if summary.get("status") in {"failed", "error"} or summary.get("validation_error_count", 0) or summary.get("details_count", 0):
        logger.warning("[workflow_tool_trace] %s", message)
    else:
        logger.info("[workflow_tool_trace] %s", message)


class MessageCollector:
    """Collects tokens and tool calls to build AssistantMessage with nested ToolStep structure.

    Structure matches frontend's ToolStep:
    - steps[]: top-level tool calls from supervisor (e.g., sql_agent, code_agent)
    - each step.subSteps[]: nested tool calls within that agent
    - content: supervisor's final text response
    """

    def __init__(self):
        self._content: str = ""  # supervisor's text content
        self._steps: list[ToolStep] = []  # top-level steps
        self._step_stack: list[ToolStep] = []  # stack for nesting
        self._pending_tool: dict[str, list[ToolStep]] = {}  # source -> pending tools

    def add_token(self, source: str, token: str) -> None:
        """Add token to content (supervisor) or as thought in current step."""
        if source == "supervisor":
            self._content += token
        elif self._step_stack:
            # Add as thought to current step's subSteps
            step = self._step_stack[-1]
            subs = step.subSteps
            if subs and subs[-1].type == "thought":
                subs[-1].thought += token
            else:
                subs.append(ToolStep(type="thought", name="Thinking", source=source, thought=token))

    def start_tool(self, source: str, name: str, input_str: str) -> None:
        """Start a tool call."""
        tool = ToolStep(type="tool", name=name, source=source, input=input_str, status="running")
        self._pending_tool.setdefault(source, []).append(tool)

        if source == "supervisor":
            # Top-level tool call
            self._steps.append(tool)
            self._step_stack = [tool]
        elif self._step_stack:
            # Attach sub-agent tools as siblings under the current top-level step
            parent = self._step_stack[0]
            parent.subSteps.append(tool)
            self._step_stack = [parent, tool]
        else:
            # Fallback: no supervisor context, treat as top-level
            self._steps.append(tool)
            self._step_stack = [tool]

    def end_tool(self, source: str, output: str) -> None:
        """End a tool call with output."""
        self._finish_tool(source, output, status="completed")

    def fail_tool(self, source: str, output: str) -> None:
        """Mark a tool call as failed."""
        self._finish_tool(source, output, status="error")

    def _finish_tool(self, source: str, output: str, *, status: Literal["completed", "error"]) -> None:
        """Finalize a pending tool call."""
        pending = self._pending_tool.get(source)
        if pending:
            tool = pending.pop(0)
            tool.output = output
            tool.status = status
            if not pending:
                self._pending_tool.pop(source, None)
            # Pop from stack if it's the current one
            if self._step_stack and self._step_stack[-1] is tool:
                self._step_stack.pop()

    def _find_top_level_tool_output(self, name: str) -> str | None:
        for step in reversed(self._steps):
            if step.type == "tool" and step.name == name and step.output:
                return step.output.strip()
        return None

    def _find_workflow_final_answer(self) -> str | None:
        payload = self._find_top_level_tool_output("workflow_agent")
        parsed = _to_single_object(payload) if payload else None
        if not isinstance(parsed, dict):
            return None
        final_answer = parsed.get("final_answer")
        if isinstance(final_answer, str) and final_answer.strip():
            return final_answer.strip()
        return None

    def has_activity(self) -> bool:
        return bool(self._content or self._steps or self._pending_tool)

    def build(self, fallback_content: str | None = None) -> AssistantMessage:
        """Build the final AssistantMessage."""
        # Mark any remaining tools as completed
        for tool_list in self._pending_tool.values():
            for tool in tool_list:
                tool.status = "completed"
        # For workflow tasks, the summary tool output is the final user-facing answer.
        # Prefer it over the supervisor's free-form completion to avoid duplicated or
        # rephrased endings after summarize_workflow_result has already produced the answer.
        final_content = (
            self._find_top_level_tool_output("summarize_workflow_result")
            or self._find_workflow_final_answer()
            or self._content
            or (fallback_content or "")
        )
        return AssistantMessage(content=final_content, steps=self._steps)

    def reset(self) -> None:
        self._content = ""
        self._steps.clear()
        self._step_stack.clear()
        self._pending_tool.clear()


class AgentCallback(AsyncCallbackHandler):
    """Async callback: publishes streaming events to EventBus, collects for message persistence."""

    def __init__(
        self,
        event_bus: EventBus,
        session_id: str,
        source: str,
        user_id: str | None = None,
        turn_id: str | None = None,
        collector: MessageCollector | None = None,
        ignore_tags: list[str] | None = None,
    ):
        self.event_bus = event_bus
        self.session_id = session_id
        self.channel = f"session:{session_id}"
        self.source = source
        self.user_id = user_id
        self.turn_id = turn_id
        self.collector = collector
        self.ignore_tags = set(ignore_tags or [])
        self._tool_stack: list[str] = []
        self._workflow_display_file: str | None = None
        try:
            self._loop = asyncio.get_running_loop()
        except RuntimeError:
            self._loop = None

    def _should_ignore(self, kwargs: dict[str, Any]) -> bool:
        return any(t in self.ignore_tags for t in (kwargs.get("tags") or []))

    async def _publish(self, event: AgentEvent) -> None:
        """Publish event to EventBus for real-time streaming."""
        event.source = self.source
        try:
            current_loop = asyncio.get_running_loop()
        except RuntimeError:
            current_loop = None

        if self._loop and current_loop is not self._loop:
            future = asyncio.run_coroutine_threadsafe(
                self.event_bus.publish(self.channel, event.model_dump_json()),
                self._loop,
            )
            await asyncio.wrap_future(future)
        else:
            await self.event_bus.publish(self.channel, event.model_dump_json())

    async def _publish_workflow_event(
        self,
        phase: str,
        payload: dict[str, Any] | None = None,
        *,
        draft_id: str | None = None,
        run_id: str | None = None,
    ) -> None:
        event_data = build_workflow_event_data(
            self.session_id,
            phase,
            payload,
            file_path=self._workflow_display_file,
            turn_id=self.turn_id,
            draft_id=draft_id,
            run_id=run_id,
        )
        logger.info(
            f"[_publish_workflow_event] phase={phase}, session={self.session_id}, file={self._workflow_display_file}"
        )
        await self._publish(
            AgentEvent(
                type=AgentEventType.WORKFLOW_EVENT,
                data=event_data,
            )
        )

    async def on_chat_model_start(self, serialized: dict, messages: list, **kwargs: Any) -> None:
        pass

    async def on_llm_new_token(self, token: str, **kwargs: Any) -> None:
        if self._should_ignore(kwargs) or not token:
            return
        await self._publish(AgentEvent(type=AgentEventType.TOKEN, content=token))
        if self.collector:
            self.collector.add_token(self.source, token)

    async def on_tool_start(self, serialized: dict, input_str: str, **kwargs: Any) -> None:
        if self._should_ignore(kwargs):
            return
        name = serialized.get("name", "unknown")
        self._tool_stack.append(name)
        # input_str can be dict or str depending on LangChain version/tool
        input_for_publish = str(input_str) if not isinstance(input_str, str) else input_str
        await self._publish(AgentEvent(type=AgentEventType.TOOL_START, data={"name": name, "input": input_for_publish}))
        payload = _to_single_object(input_str) or {}
        if self.source == "workflow_agent" and name in _WORKFLOW_TRACE_TOOL_NAMES:
            _log_workflow_tool_trace(
                _workflow_tool_trace_summary(
                    stage="start",
                    source=self.source,
                    tool_name=name,
                    session_id=self.session_id,
                    turn_id=self.turn_id,
                    payload=payload,
                )
            )
        if self.source == "workflow_agent" and name in ("create_workflow", "create_workflow_and_run", "update_workflow"):
            if isinstance(payload.get("payload"), dict):
                payload = payload.get("payload")
            workflow = _extract_workflow_definition(payload)
            if isinstance(workflow, dict):
                phase = "update_workflow" if name == "update_workflow" else "create_workflow"
                db = open_task_session()
                try:
                    draft = save_workflow_draft(
                        db,
                        session_id=self.session_id,
                        user_id=self.user_id,
                        turn_id=self.turn_id,
                        draft_id=payload.get("draft_id") if isinstance(payload.get("draft_id"), str) else None,
                        file_path=payload.get("file_path") if isinstance(payload.get("file_path"), str) else None,
                        name=payload.get("name") if isinstance(payload.get("name"), str) else None,
                        definition=workflow,
                        source="workflow_agent",
                    )
                finally:
                    db.close()
                fallback_name = None
                if isinstance(payload.get("file_path"), str):
                    fallback_name = payload["file_path"]
                elif isinstance(payload.get("name"), str):
                    fallback_name = payload["name"]
                self._workflow_display_file = draft.file_path or normalize_workflow_path(fallback_name or "workflow.json")
                await self._publish_workflow_event(
                    phase,
                    {"workflow": workflow},
                    draft_id=str(draft.id) if draft else None,
                )
        if self.collector:
            self.collector.start_tool(self.source, name, input_str)

    async def on_tool_end(self, output: Any, **kwargs: Any) -> None:
        if self._should_ignore(kwargs):
            return
        out_str = output.content if hasattr(output, "content") else str(output)
        tool_name = self._tool_stack.pop() if self._tool_stack else ""
        if self.source == "workflow_agent" and tool_name in _WORKFLOW_TRACE_TOOL_NAMES:
            _log_workflow_tool_trace(
                _workflow_tool_trace_summary(
                    stage="end",
                    source=self.source,
                    tool_name=tool_name,
                    session_id=self.session_id,
                    turn_id=self.turn_id,
                    payload=_to_single_object(out_str),
                )
            )
        await self._publish(
            AgentEvent(type=AgentEventType.TOOL_END, data={"name": tool_name, "output": out_str})
        )
        if self.collector:
            self.collector.end_tool(self.source, out_str)

    async def on_tool_error(self, error: BaseException, **kwargs: Any) -> None:
        if self._should_ignore(kwargs):
            return
        tool_name = self._tool_stack.pop() if self._tool_stack else ""
        error_message = str(error)
        if self.source == "workflow_agent" and tool_name in _WORKFLOW_TRACE_TOOL_NAMES:
            _log_workflow_tool_trace(
                {
                    "stage": "error",
                    "source": self.source,
                    "tool": tool_name,
                    "session_id": self.session_id,
                    "turn_id": self.turn_id,
                    "status": "error",
                    "error": _truncate_for_log(error_message),
                }
            )
        await self._publish(
            AgentEvent(type=AgentEventType.TOOL_ERROR, data={"name": tool_name, "error": error_message})
        )
        if self.collector:
            self.collector.fail_tool(self.source, error_message)



def persist_message(session_id: str, message: Message):
    """Persist a message (user or assistant) to session_messages table."""
    try:
        db = open_task_session()
        try:
            record = MessageRepository(db).append(session_id, message)
            logger.debug(f"[persist_message] Persisted {message.role} message for session {session_id}")
            return record
        finally:
            db.close()
    except Exception as e:
        logger.error(f"[persist_message] Failed to persist message for session {session_id}: {e}")
        return None

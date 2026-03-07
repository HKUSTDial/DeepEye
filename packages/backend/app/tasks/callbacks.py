"""Callback for Agent events: streaming + message persistence."""

import ast
import asyncio
import json
import json5
from typing import Any

from langchain_core.callbacks import AsyncCallbackHandler
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.infra import EventBus
from app.repositories import MessageRepository
from app.schemas import AgentEvent, AgentEventType, AssistantMessage, Message, ToolStep
from app.services.workflow_events import build_workflow_event_data
from deepeye.utils.logger import logger

_WORKFLOW_DIR = "/workspace/workflow"


def _to_single_object(payload: str | dict | Any) -> dict | None:
    """Parse payload to dict. Handles dict, str (JSON/JSON5/Python repr), or other types."""
    if isinstance(payload, dict):
        return payload
    if not isinstance(payload, str):
        # LangChain sometimes passes non-string types (e.g., dict objects directly)
        # Try to handle them gracefully
        if hasattr(payload, '__dict__'):
            logger.debug(f"[_to_single_object] converting object with __dict__ to dict")
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
        except Exception as e2:
            # Fallback for Python-style dict strings (single quotes)
            try:
                val = ast.literal_eval(payload)
                if isinstance(val, dict):
                    return val
            except Exception:
                pass
            logger.warning(f"[_to_single_object] all parse methods failed for payload length: {len(payload)}, preview: {payload[:300]}")
            return None


def _sanitize_workflow_name(name: str) -> str:
    base = name.strip()
    if base.lower().endswith(".json"):
        base = base[:-5]
    clean = "".join(ch for ch in base if ch.isalnum() or ch in ("-", "_"))
    if not clean:
        clean = "workflow"
    return f"{clean}.json"


def _normalize_workflow_path(path: str) -> str:
    """Normalize path to always be under WORKFLOW_DIR."""
    import os
    if not isinstance(path, str):
        return path
    clean = path.strip()
    # Extract basename to ignore agent-provided subdirectories or wrong roots
    filename = os.path.basename(clean)
    return f"{_WORKFLOW_DIR}/{_sanitize_workflow_name(filename)}"


def _get_db_session() -> Session:
    """Create a new DB session per-call to avoid fork issues in Celery workers."""
    engine = create_engine(settings.SQLALCHEMY_DATABASE_URL)
    return sessionmaker(bind=engine)()


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
        pending = self._pending_tool.get(source)
        if pending:
            tool = pending.pop(0)
            tool.output = output
            tool.status = "completed"
            if not pending:
                self._pending_tool.pop(source, None)
            # Pop from stack if it's the current one
            if self._step_stack and self._step_stack[-1] is tool:
                self._step_stack.pop()

    def build(self) -> AssistantMessage:
        """Build the final AssistantMessage."""
        # Mark any remaining tools as completed
        for tool_list in self._pending_tool.values():
            for tool in tool_list:
                tool.status = "completed"
        return AssistantMessage(content=self._content, steps=self._steps)

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
        collector: MessageCollector | None = None,
        ignore_tags: list[str] | None = None,
    ):
        self.event_bus = event_bus
        self.session_id = session_id
        self.channel = f"session:{session_id}"
        self.source = source
        self.collector = collector
        self.ignore_tags = set(ignore_tags or [])
        self._tool_stack: list[str] = []
        self._workflow_active_file: str | None = None
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

    async def _publish_workflow_event(self, phase: str, payload: dict[str, Any] | None = None) -> None:
        event_data = build_workflow_event_data(
            self.session_id,
            phase,
            payload,
            file_path=self._workflow_active_file,
        )
        logger.info(f"[_publish_workflow_event] phase={phase}, session={self.session_id}, file={self._workflow_active_file}")
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
        if self.source == "workflow_agent" and name in ("create_workflow", "update_workflow"):
            payload = _to_single_object(input_str) or {}
            if isinstance(payload.get("payload"), dict):
                payload = payload.get("payload")
            path_from_payload = payload.get("file_path") or payload.get("path") or payload.get("name")
            if isinstance(path_from_payload, str) and path_from_payload:
                self._workflow_active_file = _normalize_workflow_path(path_from_payload)
            workflow = payload.get("workflow") or payload.get("definition")
            if isinstance(workflow, dict):
                phase = "create_workflow" if name == "create_workflow" else "update_workflow"
                await self._publish_workflow_event(
                    phase,
                    {"path": self._workflow_active_file, "workflow": workflow},
                )
        if self.collector:
            self.collector.start_tool(self.source, name, input_str)

    async def on_tool_end(self, output: Any, **kwargs: Any) -> None:
        if self._should_ignore(kwargs):
            return
        out_str = output.content if hasattr(output, "content") else str(output)
        tool_name = self._tool_stack.pop() if self._tool_stack else ""
        await self._publish(
            AgentEvent(type=AgentEventType.TOOL_END, data={"name": tool_name, "output": out_str})
        )
        if self.collector:
            self.collector.end_tool(self.source, out_str)



def persist_message(session_id: str, message: Message) -> None:
    """Persist a message (user or assistant) to session_messages table."""
    try:
        db = _get_db_session()
        try:
            MessageRepository(db).append(session_id, message)
            logger.debug(f"[persist_message] Persisted {message.role} message for session {session_id}")
        finally:
            db.close()
    except Exception as e:
        logger.error(f"[persist_message] Failed to persist message for session {session_id}: {e}")

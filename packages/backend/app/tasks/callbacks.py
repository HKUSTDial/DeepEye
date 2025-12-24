"""Callback for Agent events: streaming + message persistence."""

import asyncio
from typing import Any

from langchain_core.callbacks import AsyncCallbackHandler
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.infra import EventBus
from app.repositories import MessageRepository
from app.schemas import AgentEvent, AgentEventType, AssistantMessage, Message, ToolStep


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
        self._pending_tool: dict[str, ToolStep] = {}  # source -> pending tool

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
        self._pending_tool[source] = tool

        if source == "supervisor":
            # Top-level tool call
            self._steps.append(tool)
            self._step_stack = [tool]
        elif self._step_stack:
            # Nested tool call
            self._step_stack[-1].subSteps.append(tool)
            self._step_stack.append(tool)

    def end_tool(self, source: str, output: str) -> None:
        """End a tool call with output."""
        if source in self._pending_tool:
            tool = self._pending_tool.pop(source)
            tool.output = output
            tool.status = "completed"
            # Pop from stack if it's the current one
            if self._step_stack and self._step_stack[-1] is tool:
                self._step_stack.pop()

    def build(self) -> AssistantMessage:
        """Build the final AssistantMessage."""
        # Mark any remaining tools as completed
        for tool in self._pending_tool.values():
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
        await self._publish(AgentEvent(type=AgentEventType.TOOL_START, data={"name": name, "input": input_str}))
        if self.collector:
            self.collector.start_tool(self.source, name, input_str)

    async def on_tool_end(self, output: Any, **kwargs: Any) -> None:
        if self._should_ignore(kwargs):
            return
        out_str = output.content if hasattr(output, "content") else str(output)
        await self._publish(AgentEvent(type=AgentEventType.TOOL_END, data={"output": out_str}))
        if self.collector:
            self.collector.end_tool(self.source, out_str)


def persist_message(session_id: str, message: Message) -> None:
    """Persist a message (user or assistant) to session_messages table."""
    try:
        db = _get_db_session()
        try:
            MessageRepository(db).append(session_id, message)
        finally:
            db.close()
    except Exception as e:
        print(f"[persist_message] Failed to persist message: {e}")


"""Event-sourced callback for Agent events."""

import asyncio
from typing import Any

from langchain_core.callbacks import AsyncCallbackHandler
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.infra import EventBus
from app.repositories import EventRepository
from app.schemas import AgentEvent, AgentEventType


def _get_session() -> Session:
    """Create a new session per-call to avoid fork issues in Celery workers."""
    engine = create_engine(settings.SQLALCHEMY_DATABASE_URL)
    return sessionmaker(bind=engine)()


class AgentCallback(AsyncCallbackHandler):
    """Async callback: publishes events to EventBus and persists to database."""

    def __init__(
        self,
        event_bus: EventBus,
        session_id: str,
        source: str,
        ignore_tags: list[str] | None = None,
    ):
        self.event_bus = event_bus
        self.session_id = session_id
        self.channel = f"session:{session_id}"
        self.source = source
        self.ignore_tags = set(ignore_tags or [])
        try:
            self._loop = asyncio.get_running_loop()
        except RuntimeError:
            self._loop = None

    def _should_ignore(self, kwargs: dict[str, Any]) -> bool:
        return any(t in self.ignore_tags for t in (kwargs.get("tags") or []))

    def _persist(self, event: AgentEvent) -> None:
        """Sync DB persist - runs in thread pool if needed."""
        try:
            db = _get_session()
            try:
                EventRepository(db).append(
                    self.session_id, event.type, event.source, event.content, event.data
                )
            finally:
                db.close()
        except Exception as e:
            print(
                "[AgentCallback] Failed to persist event "
                f"type={event.type} source={event.source} content={event.content} "
                f"data={event.data} error={e}"
            )

    async def emit(self, event: AgentEvent) -> None:
        """Publish to EventBus (real-time) and persist to DB (history)."""
        event.source = self.source
        print(
            "[AgentCallback] Emit event "
            f"type={event.type} source={event.source} content={event.content} data={event.data}"
        )
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
        self._persist(event)

    async def on_chat_model_start(self, serialized: dict, messages: list, **kwargs: Any) -> None:
        pass

    async def on_llm_new_token(self, token: str, **kwargs: Any) -> None:
        if self._should_ignore(kwargs) or not token:
            return
        await self.emit(AgentEvent(type=AgentEventType.TOKEN, content=token))

    async def on_tool_start(self, serialized: dict, input_str: str, **kwargs: Any) -> None:
        if self._should_ignore(kwargs):
            return
        await self.emit(AgentEvent(type=AgentEventType.TOOL_START, data={"name": serialized.get("name"), "input": input_str}))

    async def on_tool_end(self, output: Any, **kwargs: Any) -> None:
        if self._should_ignore(kwargs):
            return
        out_str = output.content if hasattr(output, "content") else str(output)
        await self.emit(AgentEvent(type=AgentEventType.TOOL_END, data={"output": out_str}))


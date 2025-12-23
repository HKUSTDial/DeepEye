"""Event-sourced callback for Agent events."""

from typing import Any

from langchain_core.callbacks import AsyncCallbackHandler
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.infra import EventBus
from app.repositories import EventRepository
from app.schemas import AgentEvent, AgentEventType


def _get_session() -> Session:
    """Create a new session per-call to avoid fork issues in Celery workers.

    Celery prefork workers fork after module import, so module-level engines
    would share connections across processes, causing "SSL SYSCALL error" or
    connection pool exhaustion. Creating engine per-call is safe and the
    overhead is negligible for event persistence.
    """
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

    def _should_ignore(self, kwargs: dict[str, Any]) -> bool:
        return any(t in self.ignore_tags for t in (kwargs.get("tags") or []))

    def _persist(self, event: AgentEvent) -> None:
        try:
            db = _get_session()
            try:
                EventRepository(db).append(self.session_id, event.type, event.source, event.content, event.data)
            finally:
                db.close()
        except Exception as e:
            print(f"[AgentCallback] Failed to persist event {event.type}: {e}")

    def emit(self, event: AgentEvent) -> None:
        """Publish to EventBus (real-time) and persist to DB (history)."""
        event.source = self.source
        self.event_bus.publish(self.channel, event.model_dump_json())
        self._persist(event)

    async def on_chat_model_start(self, serialized: dict, messages: list, **kwargs: Any) -> None:
        pass

    async def on_llm_new_token(self, token: str, **kwargs: Any) -> None:
        if self._should_ignore(kwargs) or not token:
            return
        self.emit(AgentEvent(type=AgentEventType.TOKEN, content=token))

    async def on_tool_start(self, serialized: dict, input_str: str, **kwargs: Any) -> None:
        if self._should_ignore(kwargs):
            return
        self.emit(AgentEvent(type=AgentEventType.TOOL_START, data={"name": serialized.get("name"), "input": input_str}))

    async def on_tool_end(self, output: Any, **kwargs: Any) -> None:
        if self._should_ignore(kwargs):
            return
        out_str = output.content if hasattr(output, 'content') else str(output)
        self.emit(AgentEvent(type=AgentEventType.TOOL_END, data={"output": out_str}))


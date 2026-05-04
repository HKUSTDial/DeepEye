from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any

from app.infra import EventBus
from app.schemas import AgentEvent, AgentEventType
from app.workflow.services.datasets import compact_node_outputs
from app.workflow.events import build_workflow_event_data

TrackingRefsProvider = Callable[[], dict[str, str | None]]


class WorkflowRunEventPublisher:
    """Publish workflow run events without coupling execution code to Redis details."""

    def __init__(
        self,
        event_bus: EventBus,
        session_id: str,
        *,
        workflow_path: str | None = None,
        tracking_refs: TrackingRefsProvider | None = None,
    ) -> None:
        self._event_bus = event_bus
        self._session_id = session_id
        self._workflow_path = workflow_path
        self._tracking_refs = tracking_refs or (lambda: {})

    @property
    def channel(self) -> str:
        return f"session:{self._session_id}"

    def set_workflow_path(self, workflow_path: str | None) -> None:
        self._workflow_path = workflow_path

    async def publish_event(self, event_type: AgentEventType, data: dict[str, Any] | None = None) -> None:
        event = AgentEvent(type=event_type, data=data or {})
        await self._event_bus.publish(self.channel, event.model_dump_json())

    async def publish_workflow_event(self, phase: str, payload: dict[str, Any] | None = None) -> None:
        await self.publish_event(
            AgentEventType.WORKFLOW_EVENT,
            build_workflow_event_data(
                self._session_id,
                phase,
                payload,
                file_path=self._workflow_path,
                **self._tracking_refs(),
            ),
        )

    def schedule_event(
        self,
        loop: asyncio.AbstractEventLoop,
        event_type: AgentEventType,
        data: dict[str, Any] | None = None,
    ) -> None:
        def _schedule() -> None:
            asyncio.create_task(self.publish_event(event_type, data))

        loop.call_soon_threadsafe(_schedule)

    def schedule_workflow_event(
        self,
        loop: asyncio.AbstractEventLoop,
        phase: str,
        payload: dict[str, Any] | None = None,
    ) -> None:
        def _schedule() -> None:
            asyncio.create_task(self.publish_workflow_event(phase, payload))

        loop.call_soon_threadsafe(_schedule)

    def progress_callback(self, loop: asyncio.AbstractEventLoop) -> Callable[[str], None]:
        def _publish_progress_message(message: str) -> None:
            line = message if message.endswith("\n") else message + "\n"
            self.schedule_event(
                loop,
                AgentEventType.TOKEN,
                {"content": line, "source": "workflow"},
            )

        return _publish_progress_message

    def node_start_callback(self, loop: asyncio.AbstractEventLoop) -> Callable[[str, Any, Any], None]:
        def _on_node_start(node_id: str, node_run: Any, _: Any) -> None:
            self.schedule_workflow_event(
                loop,
                "node_status",
                {"node_id": node_id, "status": node_run.status},
            )

        return _on_node_start

    def node_end_callback(self, loop: asyncio.AbstractEventLoop) -> Callable[[str, Any, Any], None]:
        def _on_node_end(node_id: str, node_run: Any, _: Any) -> None:
            self.schedule_workflow_event(
                loop,
                "node_status",
                {
                    "node_id": node_id,
                    "status": node_run.status,
                    "outputs": compact_node_outputs(node_run.outputs),
                },
            )

        return _on_node_end

"""Unified workflow event helpers."""

from __future__ import annotations

from typing import Any

from app.core.config import settings
from app.infra import RedisEventBus
from app.schemas import AgentEvent, AgentEventType
from app.workflow.artifacts import (
    extract_workflow_artifacts as extract_normalized_workflow_artifacts,
    normalize_workflow_artifact,
    normalize_workflow_artifacts,
)


def _normalize_event_payload(payload: dict[str, Any] | None) -> dict[str, Any]:
    if not payload:
        return {}
    normalized = dict(payload)
    artifact = normalized.get("artifact")
    if isinstance(artifact, dict):
        normalized["artifact"] = normalize_workflow_artifact(artifact.get("kind"), artifact)
    artifacts = normalized.get("artifacts")
    if isinstance(artifacts, list):
        normalized["artifacts"] = normalize_workflow_artifacts(artifacts)
    return normalized


def build_workflow_event_data(
    session_id: str,
    phase: str,
    payload: dict[str, Any] | None = None,
    *,
    file_path: str | None = None,
    turn_id: str | None = None,
    draft_id: str | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    metadata: dict[str, Any] = {}
    if file_path:
        metadata["file_path"] = file_path
    return {
        "version": 3,
        "session_id": session_id,
        "turn_id": turn_id,
        "draft_id": draft_id,
        "run_id": run_id,
        "phase": phase,
        "metadata": metadata,
        "payload": _normalize_event_payload(payload),
    }


async def publish_workflow_event(
    channel: str,
    session_id: str,
    phase: str,
    payload: dict[str, Any] | None = None,
    *,
    file_path: str | None = None,
    turn_id: str | None = None,
    draft_id: str | None = None,
    run_id: str | None = None,
    source: str = "workflow",
) -> None:
    bus = RedisEventBus(settings.REDIS_URL)
    try:
        event = AgentEvent(
            type=AgentEventType.WORKFLOW_EVENT,
            source=source,
            data=build_workflow_event_data(
                session_id,
                phase,
                payload,
                file_path=file_path,
                turn_id=turn_id,
                draft_id=draft_id,
                run_id=run_id,
            ),
        )
        await bus.publish(channel, event.model_dump_json())
    finally:
        await bus.close()


def publish_workflow_event_sync(
    channel: str,
    session_id: str,
    phase: str,
    payload: dict[str, Any] | None = None,
    *,
    file_path: str | None = None,
    turn_id: str | None = None,
    draft_id: str | None = None,
    run_id: str | None = None,
    source: str = "workflow",
) -> None:
    import redis

    event = AgentEvent(
        type=AgentEventType.WORKFLOW_EVENT,
        source=source,
        data=build_workflow_event_data(
            session_id,
            phase,
            payload,
            file_path=file_path,
            turn_id=turn_id,
            draft_id=draft_id,
            run_id=run_id,
        ),
    )
    redis_client = redis.Redis.from_url(settings.REDIS_URL)
    try:
        redis_client.publish(channel, event.model_dump_json())
    finally:
        redis_client.close()


def build_workflow_artifact(kind: str, **fields: Any) -> dict[str, Any]:
    return normalize_workflow_artifact(kind, fields)


def extract_workflow_artifacts(outputs: dict[str, Any] | None) -> list[dict[str, Any]]:
    return extract_normalized_workflow_artifacts(outputs)

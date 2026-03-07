"""Unified workflow event helpers."""

from __future__ import annotations

import json
import os
from typing import Any

from app.core.config import settings
from app.infra import RedisEventBus
from app.schemas import AgentEvent, AgentEventType


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
        "payload": payload or {},
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
    artifact: dict[str, Any] = {"kind": kind}
    for key, value in fields.items():
        if value in (None, "", [], {}):
            continue
        artifact[key] = value
    return artifact


def extract_workflow_artifacts(outputs: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(outputs, dict):
        return []

    artifacts: list[dict[str, Any]] = []
    for node_id, raw_outputs in outputs.items():
        if not isinstance(raw_outputs, dict):
            continue

        report_path = raw_outputs.get("report_path")
        report_html = raw_outputs.get("report_html")
        if report_path or report_html:
            artifact = build_workflow_artifact(
                "report",
                node_id=node_id,
                report_path=report_path,
                report_html=report_html,
                report_filename=os.path.basename(str(report_path)) if report_path else None,
                status=raw_outputs.get("status"),
                message=raw_outputs.get("message"),
            )
            artifacts.append(artifact)

        dashboard_url = raw_outputs.get("dashboard_url")
        if dashboard_url:
            artifacts.append(
                build_workflow_artifact(
                    "dashboard",
                    node_id=node_id,
                    dashboard_url=dashboard_url,
                    output_path=raw_outputs.get("output_path"),
                )
            )

        if raw_outputs.get("task_id") or raw_outputs.get("video_url") or raw_outputs.get("video_path"):
            artifacts.append(
                build_workflow_artifact(
                    "video",
                    node_id=node_id,
                    task_id=raw_outputs.get("task_id"),
                    video_url=raw_outputs.get("video_url"),
                    video_path=raw_outputs.get("video_path"),
                    session_id=raw_outputs.get("session_id"),
                )
            )

    return artifacts

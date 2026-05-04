"""Chat API endpoints."""

import json
import asyncio
import uuid
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from redis.asyncio import Redis
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import CurrentUserId
from app.db.session import get_db
from app.repositories import SessionRepository
from app.schemas import ChatRequest, SSEMessage
from app.runtime.services.metrics import runtime_metrics
from app.session.services.chat import start_agent_workflow
from app.session.services.session import get_or_create_session

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("")
async def start_chat(
    request: ChatRequest,
    user_id: CurrentUserId,
    db: Session = Depends(get_db),
):
    """Start chat in an existing session."""
    session_id_value = request.session_id
    if session_id_value == "current":
        session_id_value = None

    try:
        _, session_id = get_or_create_session(db, user_id, session_id_value, request.message)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    # user_message is persisted in agent_tasks.py before agent runs
    task_id = start_agent_workflow(
        session_id, 
        request.message, 
        request.datasource_ids,
    )
    return {"session_id": session_id, "task_id": task_id, "message": "Agent started"}


async def _event_generator(session_id: str) -> AsyncGenerator[str, None]:
    """Subscribe to Redis and yield SSE events with heartbeat."""
    redis_client = Redis.from_url(settings.REDIS_URL)
    pubsub = redis_client.pubsub()
    channel = f"session:{session_id}"

    await pubsub.subscribe(channel)
    runtime_metrics.increment("sse.stream.open.count", tags={"stream": "chat"})
    runtime_metrics.change_gauge("sse.stream.active", 1, tags={"stream": "chat"})

    try:
        # Initial heartbeat
        yield SSEMessage(comment="heartbeat").to_sse_string()
        
        while True:
            try:
                # Use wait_for to implement heartbeat/timeout
                # If no message for 15 seconds, send a ping
                message = await asyncio.wait_for(pubsub.get_message(ignore_subscribe_messages=True), timeout=15.0)
                
                if message is None:
                    await asyncio.sleep(0.1)
                    continue

                data_str = message["data"].decode("utf-8")
                try:
                    payload = json.loads(data_str)
                    runtime_metrics.increment("sse.stream.message.count", tags={"stream": "chat", "format": "json"})
                    yield SSEMessage(data=payload).to_sse_string()
                    # Also check for AgentEventType.AGENT_END or similar "done" markers
                    # Depending on how the end of stream is signaled
                    if payload.get("type") in ("done", "error"):
                        break
                except json.JSONDecodeError:
                    runtime_metrics.increment("sse.stream.message.count", tags={"stream": "chat", "format": "text"})
                    yield SSEMessage(data=data_str).to_sse_string()
            
            except asyncio.TimeoutError:
                # Send keep-alive heartbeat
                yield SSEMessage(comment="heartbeat").to_sse_string()
                continue
    finally:
        runtime_metrics.change_gauge("sse.stream.active", -1, tags={"stream": "chat"})
        runtime_metrics.increment("sse.stream.close.count", tags={"stream": "chat"})
        await pubsub.unsubscribe(channel)
        await redis_client.close()


@router.get("/{session_id}/stream")
async def stream_chat(
    session_id: str,
    user_id: CurrentUserId,
    db: Session = Depends(get_db),
):
    """SSE endpoint for real-time agent events."""
    try:
        session_uuid = uuid.UUID(session_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid session_id") from exc

    if not SessionRepository(db).get_by_id_and_user(session_uuid, user_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    return StreamingResponse(
        _event_generator(session_id),
        media_type="text/event-stream",
    )

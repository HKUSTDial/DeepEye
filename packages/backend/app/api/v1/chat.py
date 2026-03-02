"""Chat API endpoints."""

import json
import asyncio
from typing import AsyncGenerator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from redis.asyncio import Redis
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.schemas import ChatRequest, SSEMessage
from app.services import get_or_create_session, start_agent_workflow

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("")
async def start_chat(request: ChatRequest, db: Session = Depends(get_db)):
    """Start chat in an existing session."""
    # Session should be created via POST /api/sessions before sending messages
    # For backwards compatibility, still call get_or_create_session
    if request.session_id == "current":
        from deepeye.utils.logger import logger
        logger.warning("[chat] Received session_id='current' in ChatRequest")
    _, session_id = get_or_create_session(db, request.session_id, request.message)
    # user_message is persisted in agent_tasks.py before agent runs
    task_id = start_agent_workflow(
        session_id, 
        request.message, 
        request.datasource_ids,
        request.kb_ids
    )
    return {"session_id": session_id, "task_id": task_id, "message": "Agent started"}


async def _event_generator(session_id: str) -> AsyncGenerator[str, None]:
    """Subscribe to Redis and yield SSE events with heartbeat."""
    redis_client = Redis.from_url(settings.REDIS_URL)
    pubsub = redis_client.pubsub()
    channel = f"session:{session_id}"

    await pubsub.subscribe(channel)

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
                    yield SSEMessage(data=payload).to_sse_string()
                    # Also check for AgentEventType.AGENT_END or similar "done" markers
                    # Depending on how the end of stream is signaled
                    if payload.get("type") in ("done", "error"):
                        break
                except json.JSONDecodeError:
                    yield SSEMessage(data=data_str).to_sse_string()
            
            except asyncio.TimeoutError:
                # Send keep-alive heartbeat
                yield SSEMessage(comment="heartbeat").to_sse_string()
                continue
    finally:
        await pubsub.unsubscribe(channel)
        await redis_client.close()


@router.get("/{session_id}/stream")
async def stream_chat(session_id: str):
    """SSE endpoint for real-time agent events."""
    return StreamingResponse(
        _event_generator(session_id),
        media_type="text/event-stream",
    )

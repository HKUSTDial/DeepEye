from typing import AsyncGenerator, List, Any, Dict
from fastapi import APIRouter, HTTPException, Request, Depends, status
from fastapi.responses import StreamingResponse
from redis.asyncio import Redis
import json
import uuid
import os
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.api.schemas import ChatRequest, SSEMessage, AgentInput, ChatSessionResponse
from app.tasks.agent_tasks import run_agent_workflow
from app.db.session import get_db
from app.models.chat_session import ChatSession
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from app.core.config import settings

router = APIRouter()

@router.get("/sessions", response_model=List[ChatSessionResponse])
def list_sessions(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    List chat sessions (conversations), most recent first.
    """
    sessions = db.query(ChatSession).order_by(desc(ChatSession.updated_at)).offset(skip).limit(limit).all()
    return sessions

@router.get("/sessions/{session_id}", response_model=ChatSessionResponse)
def get_session(session_id: uuid.UUID, db: Session = Depends(get_db)):
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session

@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(session_id: uuid.UUID, db: Session = Depends(get_db)):
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    db.delete(session)
    db.commit()
    # Note: This doesn't delete the LangGraph checkpoints. 
    # That would require a raw SQL delete on the checkpoints table.
    return None

@router.get("/sessions/{session_id}/history")
async def get_session_history(session_id: str):
    """
    Retrieve message history from LangGraph checkpoints.
    """
    # Use POSTGRES_STATE_URL to connect to the checkpoints DB
    async with AsyncPostgresSaver.from_conn_string(settings.POSTGRES_STATE_URL) as checkpointer:
        # Load the latest checkpoint for the thread using async method aget_tuple
        checkpoint_tuple = await checkpointer.aget_tuple(
            {"configurable": {"thread_id": session_id}}
        )
        
        if not checkpoint_tuple or not checkpoint_tuple.checkpoint:
             return {"messages": []}

        checkpoint = checkpoint_tuple.checkpoint
        channel_values = checkpoint.get("channel_values", {})
        messages = channel_values.get("messages", [])
        
        serialized_messages = []
        for msg in messages:
             # Basic serialization for LangChain messages
             msg_data = {}
             content = ""
             type_ = "user"
             
             if hasattr(msg, "content"):
                 content = msg.content
             
             if hasattr(msg, "type"):
                 if msg.type == "human":
                     type_ = "user"
                 elif msg.type == "ai":
                     type_ = "assistant"
                 elif msg.type == "system":
                     type_ = "system"
                 elif msg.type == "tool":
                     type_ = "tool"
                 else:
                     type_ = msg.type
             
             # Construct simple message object
             msg_data = {
                 "role": type_,
                 "content": content,
                 # Additional fields if available
                 "id": getattr(msg, "id", None)
             }
             
             serialized_messages.append(msg_data)

        return {"messages": serialized_messages}


@router.post("/chat")
async def start_chat(request: ChatRequest, db: Session = Depends(get_db)):
    """
    Start a new chat session or continue an existing one.
    Triggers a background Celery task.
    """
    # 1. Manage Session Record
    session_id_str = request.session_id or str(uuid.uuid4())
    session_uuid = uuid.UUID(session_id_str)
    
    # Check if session exists
    session = db.query(ChatSession).filter(ChatSession.id == session_uuid).first()
    
    if not session:
        # Create new session
        # Use first 50 chars of message as title
        title = request.message[:50] + "..." if len(request.message) > 50 else request.message
        session = ChatSession(id=session_uuid, title=title)
        db.add(session)
    else:
        # Update updated_at manually
        session.updated_at = datetime.now(timezone.utc)
        
    db.commit()
    db.refresh(session)

    # 2. Trigger Workflow
    # Construct AgentInput
    agent_input = AgentInput(
        session_id=session_id_str,
        user_input=request.message,
        datasource_id=request.datasource_id # Pass through
    )
    
    # Trigger Celery task
    task = run_agent_workflow.delay(agent_input.model_dump())
    
    return {
        "session_id": session_id_str,
        "task_id": task.id,
        "message": "Agent started processing"
    }

async def event_generator(session_id: str, redis_url: str) -> AsyncGenerator[str, None]:
    """
    Generator that subscribes to Redis channel and yields SSE events.
    """
    redis_client = Redis.from_url(redis_url)
    pubsub = redis_client.pubsub()
    channel = f"session:{session_id}"
    
    await pubsub.subscribe(channel)
    
    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                data_str = message["data"].decode("utf-8")
                
                # SSE format: data: <content>\n\n
                try:
                    payload = json.loads(data_str)
                    
                    sse_msg = SSEMessage(data=payload)
                    yield sse_msg.to_sse_string()

                    # Check for completion signal AFTER yielding
                    if payload.get("type") == "done":
                        break
                    
                except json.JSONDecodeError:
                    # Fallback for raw strings
                    sse_msg = SSEMessage(data=data_str)
                    yield sse_msg.to_sse_string()
                
    finally:
        await pubsub.unsubscribe(channel)
        await redis_client.close()

@router.get("/chat/{session_id}/stream")
async def stream_chat(session_id: str):
    """
    SSE Endpoint. Subscribes to the agent's event stream.
    """
    return StreamingResponse(
        event_generator(session_id, settings.REDIS_URL),
        media_type="text/event-stream"
    )

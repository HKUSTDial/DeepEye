from pydantic import BaseModel, Field
from typing import Any
import json
from uuid import UUID
from enum import Enum

class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None  # If None, backend generates one
    datasource_id: str | None = None # Optional: Use specific DB connection

class AgentInput(BaseModel):
    """
    Standardized input schema for the Agent Workflow Task.
    """
    session_id: str
    user_input: str
    datasource_id: str | None = None # Future: Connect to specific DB
    # model_config: dict | None = None # Future: Temperature, Model Name, etc.

# --- DataSource Schemas ---

class DataSourceBase(BaseModel):
    name: str
    type: str  # 'postgres', 'mysql', 'sqlite', etc.
    connection_string: str

class DataSourceCreate(DataSourceBase):
    pass

class DataSourceUpdate(BaseModel):
    name: str | None = None
    type: str | None = None
    connection_string: str | None = None

class DataSourceResponse(DataSourceBase):
    id: UUID
    created_at: Any # datetime

    class Config:
        from_attributes = True

# --- Chat Session Schemas ---

class ChatSessionResponse(BaseModel):
    id: UUID
    title: str | None
    created_at: Any # datetime
    updated_at: Any # datetime

    class Config:
        from_attributes = True

# --- Agent Events ---

class AgentEventType(str, Enum):
    """
    Systematic Event Types for Frontend Rendering.
    """
    # 1. Content Streaming (LLM generation)
    TOKEN = "token" 
    
    # 2. Tool Execution (SQL, Python, Calculator, etc.)
    TOOL_START = "tool_start"
    TOOL_END = "tool_end"
    TOOL_ERROR = "tool_error"

    # 3. Agent State / Lifecycle
    AGENT_START = "agent_start"
    AGENT_END = "agent_end"
    AGENT_THOUGHT = "agent_thought" # The reasoning block before action
    
    # 4. Critical Errors
    ERROR = "error"

class AgentEvent(BaseModel):
    """
    Standard Schema for events published by the Agent (Business Layer).
    Sent via Redis Pub/Sub -> SSE (as the 'data' payload).
    """
    type: AgentEventType
    source: str = "system" # e.g. "supervisor", "sql_tool", "python_interpreter"
    content: str | None = None  # Main text content (for streaming tokens)
    data: dict[str, Any] | None = None # Full metadata or structured output
    
    class Config:
        use_enum_values = True

class SSEMessage(BaseModel):
    """
    Standard Schema for Server-Sent Events (Protocol Layer).
    """
    event: str | None = None 
    data: Any                
    id: str | None = None    
    retry: int | None = None

    def to_sse_string(self) -> str:
        lines = []
        if self.id:
            lines.append(f"id: {self.id}")
        if self.event:
            lines.append(f"event: {self.event}")
        if self.retry:
            lines.append(f"retry: {self.retry}")
            
        # Serialize data to JSON if it's not a string
        if isinstance(self.data, BaseModel):
            data_str = self.data.model_dump_json()
        elif isinstance(self.data, (dict, list, int, float, bool)) or self.data is None:
            data_str = json.dumps(self.data)
        else:
            data_str = str(self.data)
            
        lines.append(f"data: {data_str}")
        return "\n".join(lines) + "\n\n"

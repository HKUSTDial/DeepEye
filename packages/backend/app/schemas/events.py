"""Event schemas for streaming and message persistence."""

import json
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


# ============ Event Type Hierarchy ============

class EventTypeBase(str, Enum):
    """Base class for all event types."""
    pass


class AgentEventType(EventTypeBase):
    """Agent-related event types for real-time streaming."""

    TOKEN = "token"
    TOOL_START = "tool_start"
    TOOL_END = "tool_end"
    TOOL_ERROR = "tool_error"
    AGENT_START = "agent_start"
    AGENT_END = "agent_end"
    ERROR = "error"
    WORKFLOW_EVENT = "workflow_event"


class SandboxEventType(EventTypeBase):
    """Sandbox-related event types."""

    STARTED = "sandbox_started"  # Sandbox container started, open files panel
    FILES_CHANGED = "sandbox_files_changed"  # Notify frontend to refresh file list
    COMMAND_SUCCESS = "sandbox_command_success"
    COMMAND_ERROR = "sandbox_command_error"


# --- Message Models (for persistence, matches frontend ToolStep structure) ---


class ToolStep(BaseModel):
    """A tool call or thought step, can be nested."""

    type: Literal["tool", "thought"] = "tool"
    name: str = ""
    source: str = ""
    input: str = ""
    output: str = ""
    thought: str = ""
    status: Literal["running", "completed", "error"] = "completed"
    subSteps: list["ToolStep"] = Field(default_factory=list)


class UserMessage(BaseModel):
    """User message in the conversation."""

    role: Literal["user"] = "user"
    content: str


class AssistantMessage(BaseModel):
    """Assistant message with content and nested tool steps."""

    role: Literal["assistant"] = "assistant"
    content: str = ""  # supervisor's final response
    steps: list[ToolStep] = Field(default_factory=list)


Message = UserMessage | AssistantMessage


# ============ Event Models ============

class EventBase(BaseModel):
    """Base class for all events."""
    source: str = "system"
    content: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)

    model_config = {"use_enum_values": True}


class AgentEvent(EventBase):
    """Agent-related event."""
    type: AgentEventType


class SandboxEvent(EventBase):
    """Sandbox-related event."""
    type: SandboxEventType


class SSEMessage(BaseModel):
    """Server-Sent Event message"""

    event: str | None = None
    data: Any = None
    id: str | None = None
    retry: int | None = None
    comment: str | None = None

    def to_sse_string(self) -> str:
        lines = []
        if self.comment:
            lines.append(f": {self.comment}")
        if self.id:
            lines.append(f"id: {self.id}")
        if self.event:
            lines.append(f"event: {self.event}")
        if self.retry:
            lines.append(f"retry: {self.retry}")

        if self.data is not None:
            if isinstance(self.data, BaseModel):
                data_str = self.data.model_dump_json()
            elif isinstance(self.data, (dict, list, int, float, bool)):
                data_str = json.dumps(self.data)
            else:
                data_str = str(self.data)
            lines.append(f"data: {data_str}")

        return "\n".join(lines) + "\n\n"

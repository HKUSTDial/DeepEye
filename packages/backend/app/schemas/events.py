"""Agent Event schemas for streaming and message persistence."""

import json
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class AgentEventType(str, Enum):
    """Event types for real-time streaming."""

    TOKEN = "token"
    TOOL_START = "tool_start"
    TOOL_END = "tool_end"
    TOOL_ERROR = "tool_error"
    AGENT_START = "agent_start"
    AGENT_END = "agent_end"
    ERROR = "error"


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


class AgentEvent(BaseModel):
    type: AgentEventType
    source: str = "system"
    content: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)

    model_config = {"use_enum_values": True}


class SSEMessage(BaseModel):
    """Server-Sent Event message"""

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

        if isinstance(self.data, BaseModel):
            data_str = self.data.model_dump_json()
        elif isinstance(self.data, (dict, list, int, float, bool)) or self.data is None:
            data_str = json.dumps(self.data)
        else:
            data_str = str(self.data)

        lines.append(f"data: {data_str}")
        return "\n".join(lines) + "\n\n"


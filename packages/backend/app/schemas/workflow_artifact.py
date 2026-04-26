"""Typed workflow artifact protocol models."""

from __future__ import annotations

from typing import Any, Literal, cast

from pydantic import BaseModel, Field, field_validator

WorkflowArtifactStatus = Literal["pending", "running", "ready", "failed", "expired"]

_STATUS_ALIASES = {
    "complete": "ready",
    "completed": "ready",
    "done": "ready",
    "ok": "ready",
    "ready": "ready",
    "success": "ready",
    "succeeded": "ready",
    "error": "failed",
    "errored": "failed",
    "failed": "failed",
    "failure": "failed",
    "pending": "pending",
    "queued": "pending",
    "running": "running",
    "expired": "expired",
}


class WorkflowArtifactPreview(BaseModel):
    type: str
    url: str | None = None
    path: str | None = None
    content_key: str | None = None
    mime_type: str | None = None
    rows: list[Any] | None = None
    columns: list[str] | None = None

    model_config = {"extra": "allow"}


class WorkflowArtifactFile(BaseModel):
    name: str | None = None
    path: str | None = None
    url: str | None = None
    role: str | None = None
    mime_type: str | None = None

    model_config = {"extra": "allow"}


class WorkflowArtifactPayload(BaseModel):
    kind: str
    status: WorkflowArtifactStatus = "pending"
    title: str | None = None
    summary: str | None = None
    node_id: str | None = None
    preview: WorkflowArtifactPreview = Field(default_factory=lambda: WorkflowArtifactPreview(type="none"))
    files: list[WorkflowArtifactFile] = Field(default_factory=list)
    payload: dict[str, Any] = Field(default_factory=dict)

    model_config = {"extra": "allow"}

    @field_validator("kind", mode="before")
    @classmethod
    def normalize_kind(cls, value: Any) -> str:
        if isinstance(value, str) and value.strip():
            return value.strip().lower()
        return "artifact"

    @field_validator("status", mode="before")
    @classmethod
    def normalize_status(cls, value: Any) -> WorkflowArtifactStatus:
        if isinstance(value, str):
            return cast(WorkflowArtifactStatus, _STATUS_ALIASES.get(value.strip().lower(), "pending"))
        return "pending"

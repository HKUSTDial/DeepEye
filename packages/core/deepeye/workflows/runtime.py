"""Workflow runtime models."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


NodeRunStatus = Literal["pending", "running", "success", "failed", "skipped"]


class NodeRun(BaseModel):
    """Runtime state for a node execution."""

    node_id: str
    inputs: dict[str, Any] = Field(default_factory=dict)
    outputs: dict[str, Any] = Field(default_factory=dict)
    status: NodeRunStatus = "pending"
    error: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


class ExecutionContext(BaseModel):
    """Runtime state for a workflow execution."""

    workflow_id: str
    runs: dict[str, NodeRun] = Field(default_factory=dict)
    status: Literal["running", "success", "failed"] = "running"
    started_at: datetime | None = None
    finished_at: datetime | None = None

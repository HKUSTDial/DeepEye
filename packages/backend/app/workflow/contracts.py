"""Exportable workflow API contracts.

Pydantic models remain the source of truth for workflow payloads. Exported
schemas give the frontend and external integrators a stable contract to diff.
"""

from __future__ import annotations

from typing import Any

from app.schemas.workflow_artifact import (
    WorkflowArtifactFile,
    WorkflowArtifactPayload,
    WorkflowArtifactPreview,
    WorkflowArtifactStatus,
)


def workflow_contract_schemas() -> dict[str, Any]:
    """Return the public workflow contract schemas."""
    return {
        "WorkflowArtifactPayload": WorkflowArtifactPayload.model_json_schema(),
    }


__all__ = [
    "WorkflowArtifactFile",
    "WorkflowArtifactPayload",
    "WorkflowArtifactPreview",
    "WorkflowArtifactStatus",
    "workflow_contract_schemas",
]

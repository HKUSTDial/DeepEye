"""Workflow API schemas."""

from typing import Any
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.schemas.workflow_artifact import WorkflowArtifactPayload


class WorkflowCreate(BaseModel):
    name: str
    description: str | None = None
    definition: dict


class WorkflowUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    definition: dict | None = None


class WorkflowResponse(BaseModel):
    id: UUID
    name: str
    description: str | None
    definition: dict
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WorkflowRunResponse(BaseModel):
    id: UUID
    workflow_id: UUID | None
    session_id: UUID | None = None
    turn_id: UUID | None = None
    draft_id: UUID | None = None
    source: str | None = None
    file_path: str | None = None
    status: str
    result: dict | None
    artifacts: list[WorkflowArtifactPayload] | None = None
    error: str | None
    created_at: datetime
    finished_at: datetime | None

    model_config = {"from_attributes": True}


class ChatTurnResponse(BaseModel):
    id: UUID
    session_id: UUID
    user_id: UUID
    user_message_id: int | None
    assistant_message_id: int | None
    status: str
    intent_type: str | None
    input_text: str
    error: str | None
    created_at: datetime
    finished_at: datetime | None

    model_config = {"from_attributes": True}


class WorkflowDraftResponse(BaseModel):
    id: UUID
    session_id: UUID
    turn_id: UUID | None
    user_id: UUID
    source: str
    status: str
    display_name: str
    file_path: str | None
    definition: dict[str, Any]
    version: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WorkflowDraftUpsertRequest(BaseModel):
    draft_id: UUID | None = None
    name: str | None = None
    definition: dict[str, Any]


class WorkflowQueuedRunResponse(BaseModel):
    status: str
    task_id: str | None = None
    turn_id: UUID | None = None
    draft_id: UUID | None = None
    run_id: UUID | None = None
    error: str | None = None


class WorkflowArtifactResponse(BaseModel):
    id: UUID
    run_id: UUID
    session_id: UUID | None
    turn_id: UUID | None
    draft_id: UUID | None
    kind: str
    payload: WorkflowArtifactPayload
    created_at: datetime

    model_config = {"from_attributes": True}


class WorkspaceStateResponse(BaseModel):
    session_id: UUID
    turn: ChatTurnResponse | None = None
    draft: WorkflowDraftResponse | None = None
    run: WorkflowRunResponse | None = None
    artifacts: list[WorkflowArtifactResponse] = []


class WorkflowFileRunRequest(BaseModel):
    session_id: str
    path: str

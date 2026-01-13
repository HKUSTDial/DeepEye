"""Workflow API schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


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
    workflow_id: UUID
    status: str
    result: dict | None
    error: str | None
    created_at: datetime
    finished_at: datetime | None

    model_config = {"from_attributes": True}


class WorkflowTemplateParam(BaseModel):
    key: str
    required: bool = False
    placeholder: str | None = None
    default: str | int | float | None = None


class WorkflowTemplateResponse(BaseModel):
    id: str
    name: str
    description: str | None = None
    params: list[WorkflowTemplateParam] = []


class WorkflowTemplateRunRequest(BaseModel):
    params: dict


class WorkflowFileRunRequest(BaseModel):
    session_id: str
    path: str

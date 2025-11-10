"""Workflow Pydantic schemas."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, ConfigDict


class WorkflowBase(BaseModel):
    """Base workflow schema."""

    name: str = Field(..., min_length=1, max_length=255, description="Workflow name")
    description: Optional[str] = Field(None, description="Workflow description")
    version: str = Field(default="1.0.0", max_length=50, description="Workflow version")
    author: Optional[str] = Field(None, max_length=255, description="Author name")
    tags: List[str] = Field(default_factory=list, description="Tags")


class WorkflowCreate(WorkflowBase):
    """Workflow creation schema."""

    workflow_data: Dict[str, Any] = Field(..., description="Serialized workflow data from deepeye-core")


class WorkflowUpdate(BaseModel):
    """Workflow update schema."""

    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Workflow name")
    description: Optional[str] = Field(None, description="Workflow description")
    version: Optional[str] = Field(None, max_length=50, description="Workflow version")
    author: Optional[str] = Field(None, max_length=255, description="Author name")
    tags: Optional[List[str]] = Field(None, description="Tags")
    workflow_data: Optional[Dict[str, Any]] = Field(None, description="Serialized workflow data from deepeye-core")


class WorkflowResponse(WorkflowBase):
    """Workflow response schema."""

    id: str
    user_id: str
    workflow_data: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WorkflowListItem(BaseModel):
    """Workflow list item schema (simplified)."""

    id: str
    name: str
    description: Optional[str]
    version: str
    tags: List[str]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


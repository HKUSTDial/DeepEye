"""LLM model Pydantic schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class LLMModelBase(BaseModel):
    """Base LLM model schema."""

    base_url: str = Field(..., description="Base URL")
    model_endpoint_name: str = Field(..., description="Model endpoint name")
    model_name: Optional[str] = Field(None, description="Display name")


class LLMModelCreate(LLMModelBase):
    """LLM model creation schema."""

    api_key: str = Field(..., description="API Key")


class LLMModelUpdate(BaseModel):
    """LLM model update schema."""

    base_url: Optional[str] = Field(None, description="Base URL")
    api_key: Optional[str] = Field(None, description="API Key")
    model_endpoint_name: Optional[str] = Field(None, description="Model endpoint name")
    model_name: Optional[str] = Field(None, description="Display name")


class LLMModel(LLMModelBase):
    """LLM model schema."""

    id: str
    user_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


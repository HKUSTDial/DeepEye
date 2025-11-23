"""Database connection Pydantic schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class DatabaseConnectionBase(BaseModel):
    """Base database connection schema."""

    name: str = Field(..., description="Connection name")
    type: str = Field(..., description="Database type (e.g., postgres, mysql)")
    host: str = Field(..., description="Host address")
    port: int = Field(..., description="Port number")
    username: str = Field(..., description="Username")
    database: str = Field(..., description="Database name")


class DatabaseConnectionCreate(DatabaseConnectionBase):
    """Database connection creation schema."""

    password: str = Field(..., description="Password")


class DatabaseConnectionUpdate(BaseModel):
    """Database connection update schema."""

    name: Optional[str] = Field(None, description="Connection name")
    type: Optional[str] = Field(None, description="Database type")
    host: Optional[str] = Field(None, description="Host address")
    port: Optional[int] = Field(None, description="Port number")
    username: Optional[str] = Field(None, description="Username")
    password: Optional[str] = Field(None, description="Password")
    database: Optional[str] = Field(None, description="Database name")


class DatabaseConnection(DatabaseConnectionBase):
    """Database connection schema."""

    id: str
    user_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

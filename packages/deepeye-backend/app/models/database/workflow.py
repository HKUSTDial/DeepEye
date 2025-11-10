"""Workflow database models."""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, DateTime, ForeignKey, String, Text, JSON
from sqlalchemy.orm import relationship

from app.db.base import Base


class Workflow(Base):
    """Workflow model."""

    __tablename__ = "workflows"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Workflow metadata
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    version = Column(String(50), default="1.0.0", nullable=False)
    author = Column(String(255), nullable=True)
    tags = Column(JSON, nullable=True)  # List of strings
    
    # Workflow data (serialized Workflow object from deepeye-core)
    workflow_data = Column(JSON, nullable=False)  # Full workflow.to_dict() data
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    user = relationship("User", back_populates="workflows")


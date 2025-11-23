"""LLM model database models."""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.orm import relationship

from app.db.base import Base


class LLMModel(Base):
    """LLM model model."""

    __tablename__ = "llm_models"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    base_url = Column(String(512), nullable=False)
    api_key = Column(String(512), nullable=False)
    model_endpoint_name = Column(String(255), nullable=False)
    model_name = Column(String(255), nullable=True)  # Optional display name
    
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    user = relationship("User", back_populates="llm_models")


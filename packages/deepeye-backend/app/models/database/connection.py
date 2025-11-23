"""Database connection database models."""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.db.base import Base


class DatabaseConnection(Base):
    """Database connection model."""

    __tablename__ = "database_connections"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    name = Column(String(255), nullable=False)
    type = Column(String(50), nullable=False)  # e.g., 'postgres', 'mysql'
    host = Column(String(255), nullable=False)
    port = Column(Integer, nullable=False)
    username = Column(String(255), nullable=False)
    password = Column(String(255), nullable=False)
    database = Column(String(255), nullable=False)
    
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    user = relationship("User", back_populates="database_connections")
    
    table_descriptions = relationship("TableDescription", back_populates="connection", cascade="all, delete-orphan")
    business_rules = relationship("BusinessRule", back_populates="connection", cascade="all, delete-orphan")
    business_metrics = relationship("BusinessMetric", back_populates="connection", cascade="all, delete-orphan")
    example_queries = relationship("ExampleQuery", back_populates="connection", cascade="all, delete-orphan")


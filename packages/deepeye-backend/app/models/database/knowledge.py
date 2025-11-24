"""Knowledge Base database models."""

from datetime import datetime
from uuid import uuid4
from typing import List, Optional

from sqlalchemy import Column, DateTime, ForeignKey, String, Text, Boolean, ARRAY, Integer
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship, Mapped, mapped_column

from app.db.base import Base

class FileMetadata(Base):
    """File metadata model for storing file knowledge."""
    
    __tablename__ = "file_metadata"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    file_id = Column(String, ForeignKey("files.id", ondelete="CASCADE"), nullable=False, unique=True)
    
    summary = Column(Text, nullable=True)
    column_metadata = Column(JSONB, nullable=True)  # For structured files
    annotations = Column(Text, nullable=True)       # For unstructured files
    
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    file = relationship("File", back_populates="metadata_info")


class TableDescription(Base):
    """Table description model for storing table knowledge."""
    
    __tablename__ = "table_descriptions"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    connection_id = Column(String, ForeignKey("database_connections.id", ondelete="CASCADE"), nullable=False)
    
    schema_name = Column(String(255), default="public", nullable=False)
    table_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    connection = relationship("DatabaseConnection", back_populates="table_descriptions")
    columns = relationship(
        "ColumnDescription", 
        back_populates="table_description", 
        cascade="all, delete-orphan",
        order_by="ColumnDescription.position"
    )


class ColumnDescription(Base):
    """Column description model for storing column knowledge."""
    
    __tablename__ = "column_descriptions"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    table_description_id = Column(String, ForeignKey("table_descriptions.id", ondelete="CASCADE"), nullable=False)
    
    column_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    position = Column(Integer, nullable=False, default=0)  # Column position in table definition
    
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    table_description = relationship("TableDescription", back_populates="columns")


class BusinessRule(Base):
    """Business rule model for storing common SQL patterns."""
    
    __tablename__ = "business_rules"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    connection_id = Column(String, ForeignKey("database_connections.id", ondelete="CASCADE"), nullable=False)
    
    rule_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    rule_sql_snippet = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    connection = relationship("DatabaseConnection", back_populates="business_rules")


class BusinessMetric(Base):
    """Business metric model for storing calculation logic."""
    
    __tablename__ = "business_metrics"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    connection_id = Column(String, ForeignKey("database_connections.id", ondelete="CASCADE"), nullable=False)
    
    name = Column(String(255), nullable=False)
    alias = Column(ARRAY(String), nullable=True)
    description = Column(Text, nullable=False)
    definition_type = Column(String(50), nullable=False)  # SQL_FRAGMENT, NATURAL_LANGUAGE, DERIVED
    definition_sql = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    connection = relationship("DatabaseConnection", back_populates="business_metrics")


class ExampleQuery(Base):
    """Example query model for storing few-shot examples (Memory)."""
    
    __tablename__ = "example_queries"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    connection_id = Column(String, ForeignKey("database_connections.id", ondelete="CASCADE"), nullable=False)
    
    question = Column(Text, nullable=False)
    sql_logic = Column(Text, nullable=False)
    
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    connection = relationship("DatabaseConnection", back_populates="example_queries")


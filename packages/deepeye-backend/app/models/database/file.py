from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, DateTime, ForeignKey, String, BigInteger
from sqlalchemy.orm import relationship

from app.db.base import Base

class File(Base):
    """File model for storing file metadata."""
    
    __tablename__ = "files"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    filename = Column(String(255), nullable=False)
    original_name = Column(String(255), nullable=False)
    content_type = Column(String(100), nullable=True)
    size = Column(BigInteger, nullable=False)  # Size in bytes
    
    # Path in storage backend (e.g., MinIO object name)
    storage_path = Column(String(512), nullable=False)
    
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    user = relationship("User", back_populates="files")
    metadata_info = relationship("FileMetadata", back_populates="file", uselist=False, cascade="all, delete-orphan")


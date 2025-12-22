import uuid
from sqlalchemy import Column, String, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime, timezone

from app.db.session import Base

class DataSource(Base):
    __tablename__ = "data_sources"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, index=True, nullable=False)
    type = Column(String, nullable=False) # 'postgres', 'mysql', 'sqlite', etc.
    # In a real production app, this should be encrypted!
    connection_string = Column(Text, nullable=False) 
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


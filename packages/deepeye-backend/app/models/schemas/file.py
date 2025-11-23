from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict

class FileBase(BaseModel):
    filename: str
    original_name: str
    content_type: Optional[str] = None
    size: int

class FileCreate(FileBase):
    pass

class FileResponse(FileBase):
    id: str
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class FileDownload(BaseModel):
    url: str


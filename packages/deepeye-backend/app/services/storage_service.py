import logging
from io import BytesIO
from typing import List, Optional
import uuid

from fastapi import UploadFile
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.database.file import File
from deepeye.storage.backends.minio_backend import MinioBackend

logger = logging.getLogger(__name__)

class StorageService:
    def __init__(self):
        self.storage_backend = MinioBackend(
            endpoint=settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE,
        )
        # Ensure bucket exists
        try:
            self.storage_backend.create_bucket(settings.MINIO_BUCKET, exist_ok=True)
        except Exception as e:
            # Log error but don't crash, might be connectivity issue resolved later
            logger.error(f"Failed to ensure bucket exists: {e}")

    async def upload_file(
        self,
        db: AsyncSession,
        user_id: str,
        file: UploadFile,
    ) -> File:
        """Upload a file to storage and save metadata to database."""
        
        # Read file content
        content = await file.read()
        file_size = len(content)
        data = BytesIO(content)
        
        # Generate object name
        file_ext = ""
        if file.filename and "." in file.filename:
            file_ext = file.filename.split(".")[-1]
            
        object_name = f"{user_id}/{uuid.uuid4()}.{file_ext}" if file_ext else f"{user_id}/{uuid.uuid4()}"
        
        try:
            self.storage_backend.upload_file(
                bucket_name=settings.MINIO_BUCKET,
                object_name=object_name,
                data=data,
                length=file_size,
                content_type=file.content_type or "application/octet-stream",
            )
        except Exception as e:
            logger.error(f"Failed to upload file to MinIO: {e}")
            raise

        # Save metadata to DB
        db_file = File(
            user_id=user_id,
            filename=file.filename or "unnamed",
            original_name=file.filename or "unnamed",
            content_type=file.content_type,
            size=file_size,
            storage_path=object_name,
        )
        
        db.add(db_file)
        await db.commit()
        await db.refresh(db_file)
        
        return db_file

    async def get_files(
        self,
        db: AsyncSession,
        user_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[File]:
        """List files for a user."""
        stmt = (
            select(File)
            .where(File.user_id == user_id)
            .order_by(File.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_file(
        self,
        db: AsyncSession,
        file_id: str,
        user_id: str
    ) -> Optional[File]:
        """Get file metadata."""
        stmt = select(File).where(File.id == file_id, File.user_id == user_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_download_url(
        self,
        db: AsyncSession,
        file_id: str,
        user_id: str
    ) -> Optional[str]:
        """Get presigned download URL."""
        file = await self.get_file(db, file_id, user_id)
        if not file:
            return None
            
        return self.storage_backend.get_presigned_url(
            bucket_name=settings.MINIO_BUCKET,
            object_name=file.storage_path,
        )

    async def delete_file(
        self,
        db: AsyncSession,
        file_id: str,
        user_id: str
    ) -> bool:
        """Delete a file."""
        file = await self.get_file(db, file_id, user_id)
        if not file:
            return False
            
        # Delete from storage
        try:
            self.storage_backend.delete_file(
                bucket_name=settings.MINIO_BUCKET,
                object_name=file.storage_path,
            )
        except Exception as e:
            logger.error(f"Failed to delete file from MinIO: {e}")

        # Delete from DB
        stmt = delete(File).where(File.id == file_id)
        await db.execute(stmt)
        await db.commit()
        
        return True


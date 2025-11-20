from abc import ABC, abstractmethod
from datetime import timedelta
from io import BytesIO
from typing import Optional


class StorageBackend(ABC):
    """
    Abstract base class for storage backends.

    Defines the common interface for interacting with different storage systems
    like Minio, S3, or local file systems.
    """

    @abstractmethod
    def bucket_exists(self, bucket_name: str) -> bool:
        """Check if a bucket exists."""
        pass

    @abstractmethod
    def create_bucket(self, bucket_name: str, exist_ok: bool = True) -> None:
        """Create a bucket."""
        pass

    @abstractmethod
    def upload_file(
        self,
        bucket_name: str,
        object_name: str,
        data: BytesIO,
        length: int,
        content_type: str = "application/octet-stream",
    ) -> None:
        """Upload a file-like object."""
        pass

    @abstractmethod
    def download_file(self, bucket_name: str, object_name: str) -> BytesIO:
        """Download an object as a file-like object."""
        pass

    @abstractmethod
    def get_presigned_url(
        self,
        bucket_name: str,
        object_name: str,
        expires: timedelta = timedelta(days=7),
    ) -> str:
        """Get a presigned URL for an object."""
        pass

    @abstractmethod
    def delete_file(self, bucket_name: str, object_name: str) -> None:
        """Delete an object."""
        pass

    @abstractmethod
    def delete_bucket(self, bucket_name: str) -> None:
        """Delete a bucket. The bucket must be empty."""
        pass

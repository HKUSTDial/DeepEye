from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta
from io import BytesIO
from typing import Dict, Optional


@dataclass(frozen=True)
class StorageObjectMetadata:
    """Lightweight representation of an object stored in the backend."""

    size: int
    content_type: Optional[str]
    etag: Optional[str]
    last_modified: Optional[datetime]


@dataclass(frozen=True)
class StorageUploadPolicy:
    """
    A presigned policy payload that clients can use for direct-to-storage uploads.

    Attributes:
        url: The endpoint to which the client should submit the multipart/form-data POST.
        fields: The form fields that must accompany the upload request.
        expires_at: The UTC timestamp when the policy expires.
        bucket: The bucket the upload targets.
        prefix: The enforced key prefix (identity-aware isolation).
    """

    url: str
    fields: Dict[str, str]
    expires_at: datetime
    bucket: str
    prefix: str


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
    def list_objects(self, bucket_name: str, prefix: Optional[str] = None) -> list[str]:
        """List object names in a bucket."""
        pass

    @abstractmethod
    def delete_bucket(self, bucket_name: str) -> None:
        """Delete a bucket. The bucket must be empty."""
        pass

    @abstractmethod
    def stat_file(self, bucket_name: str, object_name: str) -> StorageObjectMetadata:
        """Fetch metadata for a stored object."""
        pass

    @abstractmethod
    def generate_upload_policy(
        self,
        bucket_name: str,
        object_prefix: str,
        expires: timedelta = timedelta(minutes=15),
        max_size: int = 10 * 1024 * 1024,
        content_type: Optional[str] = None,
    ) -> StorageUploadPolicy:
        """
        Generate a restricted upload policy for direct-to-storage uploads.

        Args:
            bucket_name: Target bucket.
            object_prefix: Enforced key prefix for isolation (e.g., "<user-id>/").
            expires: Policy TTL.
            max_size: Maximum object size in bytes.
            content_type: Optional required MIME type.
        """
        pass

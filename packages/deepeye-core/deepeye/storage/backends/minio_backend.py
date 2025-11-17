from datetime import timedelta
from io import BytesIO
from typing import Optional
import logging

from minio import Minio
from minio.error import S3Error

from deepeye.storage.interface import StorageBackend

logger = logging.getLogger(__name__)

class MinioBackend(StorageBackend):
    """
    Minio storage backend implementation.

    This class implements the StorageBackend interface for Minio object storage.
    """

    def __init__(
        self,
        endpoint: str,
        access_key: str,
        secret_key: str,
        secure: bool = False
    ):
        """
        Initialize the Minio client.

        Args:
            endpoint: Minio server URL (e.g., 'localhost:9000').
            access_key: Access key for Minio.
            secret_key: Secret key for Minio.
            secure: Whether to use TLS.
        """
        self._client = Minio(
            endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure
        )
        logger.info(f"Minio client initialized for endpoint: {endpoint}")

    def bucket_exists(self, bucket_name: str) -> bool:
        """Check if a bucket exists."""
        try:
            return self._client.bucket_exists(bucket_name)
        except S3Error as e:
            logger.error(f"Error checking if bucket '{bucket_name}' exists: {e}")
            raise

    def create_bucket(self, bucket_name: str, exist_ok: bool = True) -> None:
        """
        Create a bucket.

        Args:
            bucket_name: Name of the bucket to create.
            exist_ok: If True, do not raise an error if the bucket already exists.
        """
        try:
            if self.bucket_exists(bucket_name):
                if exist_ok:
                    logger.info(f"Bucket '{bucket_name}' already exists.")
                    return
                else:
                    raise FileExistsError(f"Bucket '{bucket_name}' already exists.")
            self._client.make_bucket(bucket_name)
            logger.info(f"Bucket '{bucket_name}' created successfully.")
        except S3Error as e:
            logger.error(f"Error creating bucket '{bucket_name}': {e}")
            raise

    def upload_file(
        self,
        bucket_name: str,
        object_name: str,
        data: BytesIO,
        length: int,
        content_type: str = "application/octet-stream",
    ) -> None:
        """Upload a file-like object."""
        try:
            self._client.put_object(
                bucket_name,
                object_name,
                data,
                length,
                content_type=content_type,
            )
            logger.info(f"Successfully uploaded '{object_name}' to bucket '{bucket_name}'.")
        except S3Error as e:
            logger.error(f"Error uploading '{object_name}' to '{bucket_name}': {e}")
            raise

    def download_file(self, bucket_name: str, object_name: str) -> BytesIO:
        """Download an object as a file-like object."""
        try:
            response = self._client.get_object(bucket_name, object_name)
            data = BytesIO(response.read())
            response.close()
            response.release_conn()
            logger.info(f"Successfully downloaded '{object_name}' from bucket '{bucket_name}'.")
            return data
        except S3Error as e:
            logger.error(f"Error downloading '{object_name}' from '{bucket_name}': {e}")
            raise

    def get_presigned_url(
        self,
        bucket_name: str,
        object_name: str,
        expires: timedelta = timedelta(days=7),
    ) -> str:
        """Get a presigned URL for an object."""
        try:
            url = self._client.get_presigned_url(
                "GET",
                bucket_name,
                object_name,
                expires=expires,
            )
            logger.info(f"Generated presigned URL for '{object_name}' in bucket '{bucket_name}'.")
            return url
        except S3Error as e:
            logger.error(f"Error generating presigned URL for '{object_name}': {e}")
            raise

    def delete_file(self, bucket_name: str, object_name: str) -> None:
        """Delete an object."""
        try:
            self._client.remove_object(bucket_name, object_name)
            logger.info(f"Successfully deleted '{object_name}' from bucket '{bucket_name}'.")
        except S3Error as e:
            logger.error(f"Error deleting '{object_name}' from '{bucket_name}': {e}")
            raise

    def delete_bucket(self, bucket_name: str) -> None:
        """Delete a bucket. The bucket must be empty."""
        try:
            self._client.remove_bucket(bucket_name)
            logger.info(f"Successfully deleted bucket '{bucket_name}'.")
        except S3Error as e:
            logger.error(f"Error deleting bucket '{bucket_name}': {e}")
            raise

import os
import shutil
from datetime import timedelta
from io import BytesIO
from pathlib import Path
from typing import Optional
import logging

from deepeye.storage.interface import (
    StorageBackend,
    StorageObjectMetadata,
    StorageUploadPolicy,
)

logger = logging.getLogger(__name__)


class LocalFileSystemBackend(StorageBackend):
    """
    Local file system implementation of StorageBackend.
    
    This backend maps "buckets" to subdirectories within a root workspace directory.
    It includes security checks to ensure operations do not escape the workspace.
    """

    def __init__(self, workspace_root: str):
        """
        Initialize the local file storage.

        Args:
            workspace_root: The absolute path to the local workspace directory.
        """
        self.root = Path(workspace_root).resolve()
        # Ensure the root directory exists
        self.root.mkdir(parents=True, exist_ok=True)
        logger.info(f"LocalFileSystemBackend initialized at: {self.root}")

    def _secure_path(self, bucket_name: str, object_name: str = None) -> Path:
        """
        Resolve and validate path to prevent directory traversal attacks.
        
        Args:
            bucket_name: Name of the bucket (subdirectory).
            object_name: Optional file name.

        Returns:
            Resolved Path object.

        Raises:
            ValueError: If the path attempts to escape the workspace root.
        """
        # 1. Resolve bucket path first
        bucket_path = (self.root / bucket_name).resolve()
        
        # Security Check 1: Bucket path must be inside root
        if not str(bucket_path).startswith(str(self.root)):
            raise ValueError(f"Security Error: Access denied for bucket '{bucket_name}'")

        if object_name is None:
            return bucket_path

        # 2. Resolve object path
        target_path = (bucket_path / object_name).resolve()

        # Security Check 2: Object path must be inside bucket path
        if not str(target_path).startswith(str(bucket_path)):
             raise ValueError(f"Security Error: Access denied for object '{object_name}' (Path Traversal Attempt)")
        
        return target_path

    def bucket_exists(self, bucket_name: str) -> bool:
        """Check if a bucket (subdirectory) exists."""
        try:
            path = self._secure_path(bucket_name)
            return path.exists() and path.is_dir()
        except ValueError:
            raise  # Re-raise security errors
        except Exception as e:
            logger.error(f"Error checking bucket '{bucket_name}': {e}")
            return False

    def create_bucket(self, bucket_name: str, exist_ok: bool = True) -> None:
        """Create a bucket (subdirectory)."""
        try:
            path = self._secure_path(bucket_name)
            if path.exists():
                if not exist_ok:
                    raise FileExistsError(f"Bucket '{bucket_name}' already exists.")
                return
            
            path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Local bucket '{bucket_name}' created.")
        except ValueError:
            raise  # Re-raise security errors
        except Exception as e:
            logger.error(f"Error creating local bucket '{bucket_name}': {e}")
            raise

    def delete_bucket(self, bucket_name: str) -> None:
        """Delete a bucket. The bucket must be empty."""
        try:
            path = self._secure_path(bucket_name)
            if not path.exists():
                return
            # rmdir fails if directory is not empty, which matches S3 behavior
            path.rmdir()
            logger.info(f"Local bucket '{bucket_name}' deleted.")
        except ValueError:
            raise  # Re-raise security errors
        except OSError as e:
             # Standardize error for non-empty directory
            if e.errno == 66 or "not empty" in str(e): # errno 66 is ENOTEMPTY
                 logger.error(f"Error deleting bucket '{bucket_name}': Bucket not empty")
            raise
        except Exception as e:
            logger.error(f"Error deleting local bucket '{bucket_name}': {e}")
            raise

    def list_objects(self, bucket_name: str, prefix: Optional[str] = None) -> list[str]:
        """List object names in a bucket."""
        try:
            bucket_path = self._secure_path(bucket_name)
            if not bucket_path.exists():
                raise FileNotFoundError(f"Bucket '{bucket_name}' not found")

            files = []
            # Walk through the directory
            for path in bucket_path.rglob("*"):
                if path.is_file():
                    # Calculate relative path from bucket root
                    rel_path = path.relative_to(bucket_path)
                    files.append(str(rel_path))
            
            # Filter by prefix if provided
            if prefix:
                files = [f for f in files if f.startswith(prefix)]
                
            return files
        except ValueError:
            raise  # Re-raise security errors
        except Exception as e:
            logger.error(f"Error listing objects in '{bucket_name}': {e}")
            raise

    def upload_file(
        self,
        bucket_name: str,
        object_name: str,
        data: BytesIO,
        length: int,
        content_type: str = "application/octet-stream",
    ) -> None:
        """Write stream data to a local file."""
        try:
            path = self._secure_path(bucket_name, object_name)
            # Ensure parent directories exist
            path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(path, "wb") as f:
                # If data is seekable, ensure we are at start
                if data.seekable():
                    data.seek(0)
                shutil.copyfileobj(data, f)
            
            logger.info(f"File '{object_name}' saved to local workspace.")
        except ValueError:
            raise  # Re-raise security errors
        except Exception as e:
            logger.error(f"Error saving file '{object_name}': {e}")
            raise

    def download_file(self, bucket_name: str, object_name: str) -> BytesIO:
        """Read a local file into a BytesIO stream."""
        try:
            path = self._secure_path(bucket_name, object_name)
            if not path.exists():
                raise FileNotFoundError(f"File '{object_name}' not found")
            
            with open(path, "rb") as f:
                content = f.read()
            
            return BytesIO(content)
        except ValueError:
            raise  # Re-raise security errors
        except Exception as e:
            logger.error(f"Error reading file '{object_name}': {e}")
            raise

    def delete_file(self, bucket_name: str, object_name: str) -> None:
        """Delete a local file."""
        try:
            path = self._secure_path(bucket_name, object_name)
            if path.exists():
                path.unlink()
                logger.info(f"File '{object_name}' deleted.")
        except ValueError:
            raise  # Re-raise security errors
        except Exception as e:
            logger.error(f"Error deleting file '{object_name}': {e}")
            raise

    def stat_file(self, bucket_name: str, object_name: str) -> StorageObjectMetadata:
        """Get file metadata from OS."""
        try:
            path = self._secure_path(bucket_name, object_name)
            stat = path.stat()
            return StorageObjectMetadata(
                size=stat.st_size,
                content_type=None, # Local FS doesn't store content-type natively
                etag=None,
                last_modified=None # Could convert stat.st_mtime to datetime if needed
            )
        except ValueError:
            raise  # Re-raise security errors
        except Exception as e:
            logger.error(f"Error stating file '{object_name}': {e}")
            raise

    def get_presigned_url(
        self,
        bucket_name: str,
        object_name: str,
        expires: timedelta = timedelta(days=7),
    ) -> str:
        """
        For local backend, we return the absolute file path.
        Note: This is not a web URL, but SDK users can use it directly.
        """
        try:
            path = self._secure_path(bucket_name, object_name)
            return str(path)
        except ValueError:
            raise  # Re-raise security errors
        except Exception as e:
             raise

    def generate_upload_policy(
        self,
        bucket_name: str,
        object_prefix: str,
        expires: timedelta = timedelta(minutes=15),
        max_size: int = 50 * 1024 * 1024,
        content_type: Optional[str] = None,
    ) -> StorageUploadPolicy:
        """
        Local backend does not support HTTP POST Upload Policies.
        """
        raise NotImplementedError(
            "LocalFileSystemBackend does not support generate_upload_policy. "
            "For local mode, please use direct file operations."
        )


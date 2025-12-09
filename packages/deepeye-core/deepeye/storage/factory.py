import os
from typing import Any, Dict, Optional

from deepeye.storage.interface import StorageBackend
from deepeye.storage.backends.minio_backend import MinioBackend
from deepeye.storage.backends.local_backend import LocalFileSystemBackend


def get_storage_backend(config: Dict[str, Any]) -> StorageBackend:
    """
    Factory function to initialize and return the appropriate StorageBackend.

    Args:
        config: A dictionary containing configuration parameters.
                Must include a 'type' key with value 'minio' or 'local'.

    Returns:
        An instance of a class implementing StorageBackend.

    Raises:
        ValueError: If the configuration is invalid or missing required parameters.
    """
    backend_type = config.get("type", "").lower()

    if not backend_type:
        raise ValueError("Storage configuration must include a 'type' field ('minio' or 'local').")

    if backend_type == "minio":
        required_fields = ["endpoint", "access_key", "secret_key"]
        missing = [f for f in required_fields if f not in config]
        if missing:
            raise ValueError(f"Minio configuration missing required fields: {missing}")

        return MinioBackend(
            endpoint=config["endpoint"],
            access_key=config["access_key"],
            secret_key=config["secret_key"],
            secure=config.get("secure", False)
        )

    elif backend_type == "local":
        root_dir = config.get("root_directory")
        
        # Default to ./workspace in the current working directory if not provided
        if not root_dir:
            root_dir = os.path.join(os.getcwd(), "workspace")
        
        return LocalFileSystemBackend(
            workspace_root=root_dir
        )

    else:
        raise ValueError(f"Unsupported storage type: '{backend_type}'. Supported types are 'minio', 'local'.")


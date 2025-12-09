import unittest
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

from deepeye.storage.factory import get_storage_backend
from deepeye.storage.backends.minio_backend import MinioBackend
from deepeye.storage.backends.local_backend import LocalFileSystemBackend


class TestStorageFactory(unittest.TestCase):
    @patch('deepeye.storage.factory.MinioBackend')
    def test_get_minio_backend(self, MockMinioBackend):
        config = {
            "type": "minio",
            "endpoint": "localhost:9000",
            "access_key": "user",
            "secret_key": "pass"
        }
        backend = get_storage_backend(config)
        MockMinioBackend.assert_called_once()
        # Since we mocked the class, the return value is a mock instance
        # In real code, isinstance(backend, MinioBackend) would be true

    def test_get_minio_backend_missing_config(self):
        config = {
            "type": "minio",
            "endpoint": "localhost:9000"
            # Missing keys
        }
        with self.assertRaises(ValueError):
            get_storage_backend(config)

    def test_get_local_backend(self):
        config = {
            "type": "local",
            "root_directory": "/tmp/test"
        }
        backend = get_storage_backend(config)
        self.assertIsInstance(backend, LocalFileSystemBackend)
        # Verify the path was set correctly (although accessing private attr is discouraged, it's ok for test)
        # Resolve path to handle OS-specific symlinks (e.g. /tmp -> /private/tmp on macOS)
        expected_path = str(Path("/tmp/test").resolve())
        self.assertEqual(str(backend.root), expected_path)

    def test_get_local_backend_default_config(self):
        config = {
            "type": "local"
            # Missing root_directory, should default to ./workspace
        }
        backend = get_storage_backend(config)
        self.assertIsInstance(backend, LocalFileSystemBackend)
        
        expected_path = os.path.join(os.getcwd(), "workspace")
        self.assertEqual(str(backend.root), expected_path)

    def test_invalid_type(self):
        with self.assertRaises(ValueError):
            get_storage_backend({"type": "invalid"})

if __name__ == "__main__":
    unittest.main()


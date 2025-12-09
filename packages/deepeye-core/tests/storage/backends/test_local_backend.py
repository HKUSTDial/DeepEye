import os
import shutil
import tempfile
import unittest
from io import BytesIO
from pathlib import Path

from deepeye.storage.backends.local_backend import LocalFileSystemBackend


class TestLocalFileSystemBackend(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for the workspace
        self.workspace_dir = tempfile.mkdtemp()
        self.backend = LocalFileSystemBackend(self.workspace_dir)
        self.bucket_name = "test-bucket"
        self.object_name = "test-file.txt"

    def tearDown(self):
        # Cleanup the temporary directory
        shutil.rmtree(self.workspace_dir)

    def test_bucket_creation_and_deletion(self):
        # Test creation
        self.backend.create_bucket(self.bucket_name)
        bucket_path = Path(self.workspace_dir) / self.bucket_name
        self.assertTrue(bucket_path.exists())
        self.assertTrue(bucket_path.is_dir())
        self.assertTrue(self.backend.bucket_exists(self.bucket_name))

        # Test deletion
        self.backend.delete_bucket(self.bucket_name)
        self.assertFalse(bucket_path.exists())
        self.assertFalse(self.backend.bucket_exists(self.bucket_name))

    def test_file_upload_and_download(self):
        self.backend.create_bucket(self.bucket_name)
        
        data = b"Hello, Local Storage!"
        self.backend.upload_file(
            self.bucket_name, 
            self.object_name, 
            BytesIO(data), 
            len(data)
        )

        file_path = Path(self.workspace_dir) / self.bucket_name / self.object_name
        self.assertTrue(file_path.exists())

        # Test download
        downloaded = self.backend.download_file(self.bucket_name, self.object_name)
        self.assertEqual(downloaded.read(), data)

    def test_list_objects(self):
        self.backend.create_bucket(self.bucket_name)
        
        # Create nested structure
        self.backend.upload_file(self.bucket_name, "file1.txt", BytesIO(b"1"), 1)
        self.backend.upload_file(self.bucket_name, "folder/file2.txt", BytesIO(b"2"), 1)

        objects = self.backend.list_objects(self.bucket_name)
        self.assertIn("file1.txt", objects)
        self.assertIn(os.path.join("folder", "file2.txt"), objects)

    def test_security_path_traversal(self):
        """Verify that accessing files outside the workspace raises an error."""
        # Try to access a file outside the workspace (e.g., /etc/passwd or parent dir)
        # We try to access the parent directory of the workspace
        
        # 1. Bucket traversal
        with self.assertRaises(ValueError):
            self.backend.bucket_exists("../outside_bucket")

        # 2. File traversal
        self.backend.create_bucket(self.bucket_name)
        with self.assertRaises(ValueError):
            self.backend.upload_file(self.bucket_name, "../pwned.txt", BytesIO(b"x"), 1)
        
        with self.assertRaises(ValueError):
            self.backend.download_file(self.bucket_name, "../../sensitive_file")

    def test_generate_upload_policy_not_supported(self):
        with self.assertRaises(NotImplementedError):
            self.backend.generate_upload_policy(self.bucket_name, "prefix")

if __name__ == "__main__":
    unittest.main()


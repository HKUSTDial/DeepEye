import unittest
from unittest.mock import MagicMock, patch
from io import BytesIO
from datetime import timedelta

from deepeye.storage.backends.minio_backend import MinioBackend, S3Error

class TestMinioBackend(unittest.TestCase):
    """Unit tests for the MinioBackend."""

    @patch('deepeye.storage.backends.minio_backend.Minio')
    def setUp(self, MockMinio):
        """Set up a test instance of MinioBackend with a mocked client."""
        self.mock_minio_client = MockMinio.return_value
        self.backend = MinioBackend(
            endpoint='localhost:9000',
            access_key='test_access_key',
            secret_key='test_secret_key',
            secure=False
        )
        self.bucket_name = 'test-bucket'
        self.object_name = 'test-object.txt'

    def test_bucket_exists(self):
        """Test bucket_exists method."""
        self.mock_minio_client.bucket_exists.return_value = True
        self.assertTrue(self.backend.bucket_exists(self.bucket_name))
        self.mock_minio_client.bucket_exists.assert_called_once_with(self.bucket_name)

    def test_bucket_does_not_exist(self):
        """Test bucket_exists when bucket does not exist."""
        self.mock_minio_client.bucket_exists.return_value = False
        self.assertFalse(self.backend.bucket_exists(self.bucket_name))

    def test_create_bucket_if_not_exists(self):
        """Test create_bucket when bucket does not exist."""
        self.mock_minio_client.bucket_exists.return_value = False
        self.backend.create_bucket(self.bucket_name)
        self.mock_minio_client.make_bucket.assert_called_once_with(self.bucket_name)

    def test_create_bucket_if_exists_ok(self):
        """Test create_bucket when bucket exists and exist_ok is True."""
        self.mock_minio_client.bucket_exists.return_value = True
        self.backend.create_bucket(self.bucket_name, exist_ok=True)
        self.mock_minio_client.make_bucket.assert_not_called()

    def test_create_bucket_if_exists_not_ok(self):
        """Test create_bucket when bucket exists and exist_ok is False."""
        self.mock_minio_client.bucket_exists.return_value = True
        with self.assertRaises(FileExistsError):
            self.backend.create_bucket(self.bucket_name, exist_ok=False)

    def test_upload_file(self):
        """Test upload_file method."""
        file_data = b"hello world"
        data_stream = BytesIO(file_data)
        self.backend.upload_file(
            self.bucket_name,
            self.object_name,
            data_stream,
            len(file_data)
        )
        self.mock_minio_client.put_object.assert_called_once_with(
            self.bucket_name,
            self.object_name,
            data_stream,
            len(file_data),
            content_type='application/octet-stream'
        )

    def test_download_file(self):
        """Test download_file method."""
        file_data = b"hello world"
        mock_response = MagicMock()
        mock_response.read.return_value = file_data
        self.mock_minio_client.get_object.return_value = mock_response

        downloaded_stream = self.backend.download_file(self.bucket_name, self.object_name)
        
        self.assertEqual(downloaded_stream.read(), file_data)
        self.mock_minio_client.get_object.assert_called_once_with(self.bucket_name, self.object_name)
        mock_response.close.assert_called_once()
        mock_response.release_conn.assert_called_once()

    def test_get_presigned_url(self):
        """Test get_presigned_url method."""
        expected_url = 'http://example.com/presigned-url'
        self.mock_minio_client.get_presigned_url.return_value = expected_url

        url = self.backend.get_presigned_url(self.bucket_name, self.object_name)

        self.assertEqual(url, expected_url)
        self.mock_minio_client.get_presigned_url.assert_called_once_with(
            'GET',
            self.bucket_name,
            self.object_name,
            expires=timedelta(days=7)
        )

    def test_delete_file(self):
        """Test delete_file method."""
        self.backend.delete_file(self.bucket_name, self.object_name)
        self.mock_minio_client.remove_object.assert_called_once_with(self.bucket_name, self.object_name)

    def test_delete_bucket(self):
        """Test delete_bucket method."""
        self.backend.delete_bucket(self.bucket_name)
        self.mock_minio_client.remove_bucket.assert_called_once_with(self.bucket_name)

if __name__ == '__main__':
    unittest.main()

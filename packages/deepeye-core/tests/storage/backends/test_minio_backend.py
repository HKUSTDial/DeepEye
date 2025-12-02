import unittest
from unittest.mock import MagicMock, patch
from io import BytesIO
from datetime import datetime, timedelta

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

    @patch('deepeye.storage.backends.minio_backend.datetime')
    @patch('deepeye.storage.backends.minio_backend.PostPolicy')
    def test_generate_upload_policy(self, MockPostPolicy, mock_datetime):
        """Test generate_upload_policy method."""
        mock_datetime.utcnow.return_value = datetime(2024, 1, 1)
        policy_instance = MockPostPolicy.return_value
        self.mock_minio_client.presigned_post_policy.return_value = {"policy": "value"}
        
        # Manually constructed the URL in the implementation, so no need to mock _base_url anymore
        prefix = "user_123"
        expected_normalized_prefix = "user_123/"

        result = self.backend.generate_upload_policy(
            bucket_name=self.bucket_name,
            object_prefix=prefix,
            expires=timedelta(minutes=5),
            max_size=1024,
            content_type="text/plain",
        )

        MockPostPolicy.assert_called_once()
        # Verify starts-with condition for the key
        policy_instance.add_starts_with_condition.assert_any_call("key", expected_normalized_prefix)
        policy_instance.add_equals_condition.assert_any_call("Content-Type", "text/plain")
        policy_instance.add_content_length_range_condition.assert_called_once_with(0, 1024)
        self.mock_minio_client.presigned_post_policy.assert_called_once_with(policy_instance)
        
        self.assertEqual(result.url, f"http://localhost:9000/{self.bucket_name}")
        self.assertEqual(result.fields, {"policy": "value"})

    @patch('deepeye.storage.backends.minio_backend.datetime')
    @patch('deepeye.storage.backends.minio_backend.PostPolicy')
    def test_generate_upload_policy_multi_user_isolation(self, MockPostPolicy, mock_datetime):
        """Test that policies generated for different users have distinct prefixes."""
        mock_datetime.utcnow.return_value = datetime(2024, 1, 1)
        # We need separate mock instances for each call to verify them independently
        policy_alice = MagicMock()
        policy_bob = MagicMock()
        MockPostPolicy.side_effect = [policy_alice, policy_bob]
        
        self.mock_minio_client.presigned_post_policy.return_value = {"policy": "dummy"}
        
        # 1. Generate for Alice
        self.backend.generate_upload_policy(self.bucket_name, "user_alice")
        
        # 2. Generate for Bob
        self.backend.generate_upload_policy(self.bucket_name, "user_bob")

        # Verify Alice's policy
        policy_alice.add_starts_with_condition.assert_any_call("key", "user_alice/")
        # Ensure Alice's policy definitely does NOT contain Bob's prefix (sanity check)
        with self.assertRaises(AssertionError):
            policy_alice.add_starts_with_condition.assert_any_call("key", "user_bob/")

        # Verify Bob's policy
        policy_bob.add_starts_with_condition.assert_any_call("key", "user_bob/")

    def test_stat_file(self):
        """Test stat_file returns metadata."""
        mock_stat = MagicMock()
        mock_stat.size = 128
        mock_stat.content_type = "text/csv"
        mock_stat.etag = "etag123"
        mock_stat.last_modified = datetime(2024, 1, 1)
        self.mock_minio_client.stat_object.return_value = mock_stat

        metadata = self.backend.stat_file(self.bucket_name, self.object_name)

        self.mock_minio_client.stat_object.assert_called_once_with(self.bucket_name, self.object_name)
        self.assertEqual(metadata.size, 128)
        self.assertEqual(metadata.content_type, "text/csv")
        self.assertEqual(metadata.etag, "etag123")

if __name__ == '__main__':
    unittest.main()

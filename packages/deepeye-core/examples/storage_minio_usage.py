"""
This is an example script demonstrating how to use the MinioBackend for file storage.
It has three modes, controlled by command-line arguments:
    --setup    : Creates a bucket and uploads a sample file from the `data` directory. For example:
                 `python examples/storage_minio_usage.py --setup`
    --download : Downloads the file, saves it locally, and verifies its content. For example:
                 `python examples/storage_minio_usage.py --download`
    --cleanup  : Deletes the file and the bucket created by the setup process. For example:
                 `python examples/storage_minio_usage.py --cleanup`
Prerequisites:
1. Make sure you have a Minio server running. You can start one using the
   docker-compose file in `packages/deepeye-backend/docker-compose.yml`:
   `docker-compose up -d minio`
2. Ensure the required environment variables are set or use the default values
   for the local Minio instance. The script will use the following configuration:
   - MINIO_ENDPOINT: 'localhost:9000'
   - MINIO_ACCESS_KEY: 'minioadmin'
   - MINIO_SECRET_KEY: 'minioadmin'
   - MINIO_SECURE: False
"""
import os
import logging
import argparse
from deepeye.storage.backends.minio_backend import MinioBackend

# --- Configuration ---
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
MINIO_SECURE = os.getenv("MINIO_SECURE", "False").lower() in ('true', '1', 't')

# --- Setup Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Demo Parameters ---
BUCKET_NAME = "storage-minio-test-bucket"
# Use a real file from the examples/data directory
SAMPLE_FILE_PATH = os.path.join(os.path.dirname(__file__), "data", "employees.csv")
DOWNLOADED_FILE_PATH = os.path.join(os.path.dirname(__file__), "data", "employees_downloaded.csv")
OBJECT_NAME = os.path.basename(SAMPLE_FILE_PATH)

def get_backend():
    """Initializes and returns the MinioBackend."""
    try:
        backend = MinioBackend(
            endpoint=MINIO_ENDPOINT,
            access_key=MINIO_ACCESS_KEY,
            secret_key=MINIO_SECRET_KEY,
            secure=MINIO_SECURE
        )
        logging.info("Successfully initialized MinioBackend.")
        return backend
    except Exception as e:
        logging.error(f"Failed to initialize MinioBackend: {e}")
        logging.error("Please ensure your Minio Docker container is running.")
        return None

def run_setup(storage_backend):
    """Create bucket and upload a sample file."""
    logging.info("--- Running Setup ---")
    
    # 1. Create a bucket
    logging.info(f"Attempting to create bucket: '{BUCKET_NAME}'")
    storage_backend.create_bucket(BUCKET_NAME, exist_ok=True)
    assert storage_backend.bucket_exists(BUCKET_NAME), f"Bucket '{BUCKET_NAME}' should exist now."
    logging.info(f"Bucket '{BUCKET_NAME}' is ready.")

    # 2. Upload the file
    if not os.path.exists(SAMPLE_FILE_PATH):
        logging.error(f"Sample file not found at: {SAMPLE_FILE_PATH}")
        return

    file_size = os.path.getsize(SAMPLE_FILE_PATH)
    with open(SAMPLE_FILE_PATH, "rb") as f:
        logging.info(f"Uploading '{OBJECT_NAME}' to bucket '{BUCKET_NAME}'...")
        storage_backend.upload_file(
            bucket_name=BUCKET_NAME,
            object_name=OBJECT_NAME,
            data=f,
            length=file_size
        )
    logging.info("File uploaded successfully.")

    # 3. Get and display a presigned URL
    logging.info(f"Generating a presigned URL for '{OBJECT_NAME}'...")
    presigned_url = storage_backend.get_presigned_url(BUCKET_NAME, OBJECT_NAME)
    logging.info(f"Presigned URL (valid for 7 days): {presigned_url}")
    logging.info("You can now see the uploaded file in the Minio Console: http://localhost:9001")
    logging.info("--- Setup Finished ---")

def run_download(storage_backend):
    """Downloads the sample file, saves it, verifies it, and cleans up."""
    logging.info("--- Running Download & Verification ---")
    try:
        logging.info(f"Downloading '{OBJECT_NAME}' from bucket '{BUCKET_NAME}'...")
        downloaded_stream = storage_backend.download_file(BUCKET_NAME, OBJECT_NAME)
        
        # Save the downloaded file locally
        with open(DOWNLOADED_FILE_PATH, "wb") as f:
            f.write(downloaded_stream.getbuffer())
        logging.info(f"File successfully downloaded to: {DOWNLOADED_FILE_PATH}")

        # Verify content by comparing with the original file
        logging.info("Verifying file content...")
        with open(SAMPLE_FILE_PATH, "rb") as f_orig, open(DOWNLOADED_FILE_PATH, "rb") as f_down:
            original_content = f_orig.read()
            downloaded_content = f_down.read()
        
        if original_content == downloaded_content:
            logging.info("✅ Verification successful: Downloaded file content matches the original.")
        else:
            logging.error("❌ Verification failed: Downloaded file content does not match the original.")
        
    except Exception as e:
        logging.error(f"An error occurred during download: {e}", exc_info=True)
    # finally:
    #     # Clean up the locally downloaded file
    #     if os.path.exists(DOWNLOADED_FILE_PATH):
    #         os.remove(DOWNLOADED_FILE_PATH)
    #         logging.info(f"Cleaned up local downloaded file: {DOWNLOADED_FILE_PATH}")
    
    logging.info("--- Download & Verification Finished ---")

def run_cleanup(storage_backend):
    """Delete the object and the bucket."""
    logging.info("--- Running Cleanup ---")
    try:
        logging.info(f"Deleting object '{OBJECT_NAME}' from bucket '{BUCKET_NAME}'...")
        storage_backend.delete_file(BUCKET_NAME, OBJECT_NAME)
        logging.info(f"Object '{OBJECT_NAME}' deleted.")

        logging.info(f"Deleting bucket '{BUCKET_NAME}'...")
        storage_backend.delete_bucket(BUCKET_NAME)
        logging.info(f"Bucket '{BUCKET_NAME}' deleted.")
    except Exception as e:
        logging.error(f"An error occurred during cleanup: {e}", exc_info=True)
    
    logging.info("--- Cleanup Finished ---")

def main():
    parser = argparse.ArgumentParser(description="MinioBackend usage example script.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--setup", action="store_true", help="Run the setup process: create bucket and upload file.")
    group.add_argument("--download", action="store_true", help="Download the sample file and verify its content.")
    group.add_argument("--cleanup", action="store_true", help="Run the cleanup process: delete file and bucket.")

    args = parser.parse_args()

    storage_backend = get_backend()
    if not storage_backend:
        return

    if args.setup:
        run_setup(storage_backend)
    elif args.download:
        run_download(storage_backend)
    elif args.cleanup:
        run_cleanup(storage_backend)

if __name__ == "__main__":
    main()

"""
This is an example script demonstrating how to use the MinioBackend for file storage.
It has three modes, controlled by command-line arguments:
    --setup    : Creates a bucket and uploads a sample file from the `data` directory. For example:
                 `python examples/storage_minio_usage.py --setup`
    --download : Downloads the file, saves it locally, and verifies its content. For example:
                 `python examples/storage_minio_usage.py --download`
    --iam-upload : Demonstrates the IAM-optimized direct upload flow (Backend generates policy -> Frontend uploads directly).
                   This also tests that uploading to an unauthorized folder is blocked.
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
import requests
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

def run_iam_upload(storage_backend):
    """Demonstrate direct upload using IAM policy (simulating frontend) with multiple users."""
    logging.info("--- Running IAM Policy Direct Upload (Multi-User Scenario) ---")

    def perform_upload(user_name, policy_data, target_key, file_path, expect_success=True):
        """Helper to perform upload and log result."""
        upload_url = policy_data.url
        form_fields = policy_data.fields.copy()
        form_fields['key'] = target_key
        
        files = {
            'file': (os.path.basename(file_path), open(file_path, 'rb'))
        }
        
        action_desc = f"User '{user_name}' uploading to '{target_key}'"
        logging.info(f"{action_desc}...")
        
        try:
            response = requests.post(upload_url, data=form_fields, files=files)
            if response.status_code == 204:
                if expect_success:
                    logging.info(f"✅ SUCCESS: {action_desc} succeeded as expected.")
                else:
                    logging.error(f"❌ FAILURE: {action_desc} succeeded but SHOULD HAVE FAILED!")
            else:
                if expect_success:
                    logging.error(f"❌ FAILURE: {action_desc} failed: {response.status_code} - {response.text}")
                else:
                    logging.info(f"✅ SECURITY SUCCESS: ⚠️ {action_desc} blocked with status {response.status_code} (Expected Forbidden)")
        except Exception as e:
            if expect_success:
                logging.error(f"❌ Exception during {action_desc}: {e}")
            else:
                logging.info(f"✅ SECURITY SUCCESS: ⚠️ {action_desc} blocked ({e})")

    # --- Scenario 1: Alice uploads `company_data.xlsx` to her own folder ---
    alice_id = "user_alice"
    alice_prefix = f"{alice_id}/"
    logging.info(f"\n[Step 1] Generating upload policy for Alice (prefix: '{alice_prefix}')...")
    
    alice_policy = storage_backend.generate_upload_policy(
        bucket_name=BUCKET_NAME,
        object_prefix=alice_prefix
    )
    alice_file = os.path.join(os.path.dirname(__file__), "data", "company_data.xlsx")
    perform_upload(
        user_name="Alice",
        policy_data=alice_policy,
        target_key=f"{alice_prefix}company_data.xlsx",
        file_path=alice_file,
        expect_success=True
    )

    # --- Scenario 2: Alice tries to upload `company_data.xlsx` to Bob's folder (simulating attacker, expected to be blocked) ---
    bob_id = "user_bob"
    bob_prefix = f"{bob_id}/"
    logging.info(f"\n[Step 2] Security Test: Alice attempting to upload to Bob's folder ('{bob_prefix}')...")
    perform_upload(
        user_name="Alice (Attacker)",
        policy_data=alice_policy,  # Using Alice's policy!
        target_key=f"{bob_prefix}company_data.xlsx",
        file_path=alice_file,
        expect_success=False
    )

    # --- Scenario 3: Bob uploads `sales.json` to his own folder ---
    logging.info(f"\n[Step 3] Generating upload policy for Bob (prefix: '{bob_prefix}')...")
    
    bob_policy = storage_backend.generate_upload_policy(
        bucket_name=BUCKET_NAME,
        object_prefix=bob_prefix
    )
    bob_file = os.path.join(os.path.dirname(__file__), "data", "sales.json")
    perform_upload(
        user_name="Bob",
        policy_data=bob_policy,
        target_key=f"{bob_prefix}sales.json",
        file_path=bob_file,
        expect_success=True
    )

    logging.info("\n--- IAM Policy Demo Finished ---")

def run_cleanup(storage_backend):
    """Delete all objects and the bucket."""
    logging.info("--- Running Cleanup ---")
    try:
        # 1. List all objects
        logging.info(f"Listing all objects in bucket '{BUCKET_NAME}'...")
        try:
            objects = storage_backend.list_objects(BUCKET_NAME)
        except Exception as e:
            # If bucket doesn't exist, we can't list objects, so just return
            if "NoSuchBucket" in str(e):
                logging.warning(f"Bucket '{BUCKET_NAME}' does not exist. Cleanup skipped.")
                return
            raise e

        # 2. Delete all objects
        if objects:
            logging.info(f"Found {len(objects)} objects to delete.")
            for obj_name in objects:
                logging.info(f"Deleting object '{obj_name}'...")
                storage_backend.delete_file(BUCKET_NAME, obj_name)
        else:
            logging.info("Bucket is already empty.")

        # 3. Delete the bucket
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
    group.add_argument("--iam-upload", action="store_true", help="Run IAM-optimized direct upload demo.")
    group.add_argument("--cleanup", action="store_true", help="Run the cleanup process: delete file and bucket.")

    args = parser.parse_args()

    storage_backend = get_backend()
    if not storage_backend:
        return

    if args.setup:
        run_setup(storage_backend)
    elif args.download:
        run_download(storage_backend)
    elif args.iam_upload:
        run_iam_upload(storage_backend)
    elif args.cleanup:
        run_cleanup(storage_backend)

if __name__ == "__main__":
    main()

"""
This example demonstrates how to use the LocalFileSystemBackend for file storage.
This is particularly useful for SDK users running the application locally,
where files are stored in a local 'workspace' directory instead of a remote server.
It has several modes, controlled by command-line arguments:
    --setup    : Creates a bucket and uploads a sample file from the `data` directory. For example:
                 `python examples/storage_local_usage.py --setup`
    --upload : Uploads the sample file to the bucket. For example:
                 `python examples/storage_local_usage.py --upload`
    --list : Lists the files in the bucket. For example:
                 `python examples/storage_local_usage.py --list`
    --download : Downloads the file from the bucket. For example:
                 `python examples/storage_local_usage.py --download`
    --cleanup  : Deletes the file and the bucket created by the setup process. For example:
                 `python examples/storage_local_usage.py --cleanup`
Features:
- Supports setup, upload, list, download, and cleanup operations via command-line arguments.
- Uses real files from the 'examples/data' directory for demonstration.
- Ensures operations are confined within the 'workspace' directory.
Prerequisites:
    None. The script will automatically create a 'workspace' directory in your current path.
"""
import os
import argparse
import shutil
import logging
from io import BytesIO

from deepeye.storage.factory import get_storage_backend

# --- Setup Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Configuration ---
BUCKET_NAME = "demo-project"
# Use a real file from the examples/data directory
SAMPLE_FILE_PATH = os.path.join(os.path.dirname(__file__), "data", "employees.csv")
OBJECT_NAME = os.path.basename(SAMPLE_FILE_PATH)

def get_backend():
    """Initializes and returns the LocalFileSystemBackend."""
    # We don't specify 'root_directory', so it defaults to ./workspace
    config = {
        "type": "local"
        # "root_directory": "/custom/path/if/needed" 
    }
    
    try:
        storage = get_storage_backend(config)
        logging.info(f"Initialized Local Storage at: {storage.root}")
        return storage
    except Exception as e:
        logging.error(f"Failed to initialize storage: {e}")
        return None

def run_setup(storage):
    """Create the demo bucket."""
    logging.info("--- Running Setup ---")
    try:
        logging.info(f"Creating bucket (folder): '{BUCKET_NAME}'")
        storage.create_bucket(BUCKET_NAME, exist_ok=True)
        
        # Verify
        bucket_path = os.path.join(storage.root, BUCKET_NAME)
        if os.path.exists(bucket_path):
             logging.info(f"✅ Bucket created at: {bucket_path}")
        else:
             logging.error("❌ Bucket creation failed verification.")
             
    except Exception as e:
        logging.error(f"Setup failed: {e}")
    logging.info("--- Setup Finished ---")

def run_upload(storage):
    """
    Upload a sample file.
    
    NOTE for SDK Users:
    In a real local workflow, you often don't need to write code to 'upload' files.
    You can simply copy/paste your files into the 'workspace/demo-project' directory
    using your operating system's file manager.
    
    This function demonstrates how the system programmatically writes files,
    which is useful for saving intermediate results or generated reports.
    """
    logging.info("--- Running Upload ---")
    if not os.path.exists(SAMPLE_FILE_PATH):
        logging.error(f"Sample file not found at: {SAMPLE_FILE_PATH}")
        return

    try:
        file_size = os.path.getsize(SAMPLE_FILE_PATH)
        logging.info(f"Uploading '{OBJECT_NAME}' to bucket '{BUCKET_NAME}'...")
        
        with open(SAMPLE_FILE_PATH, "rb") as f:
            storage.upload_file(
                BUCKET_NAME, 
                OBJECT_NAME, 
                f, 
                file_size
            )
        
        # Verify file exists on disk
        expected_path = os.path.join(storage.root, BUCKET_NAME, OBJECT_NAME)
        if os.path.exists(expected_path):
            logging.info(f"✅ File uploaded and verified on disk at: {expected_path}")
        else:
            logging.error("❌ File NOT found on disk after upload!")
            
    except Exception as e:
        logging.error(f"Upload failed: {e}")
    logging.info("--- Upload Finished ---")

def run_list(storage):
    """List files in the bucket."""
    logging.info("--- Running List ---")
    try:
        files = storage.list_objects(BUCKET_NAME)
        logging.info(f"Files in '{BUCKET_NAME}':")
        if not files:
            logging.info("  (empty)")
        for f in files:
            logging.info(f"  - {f}")
    except Exception as e:
        logging.error(f"List failed: {e}")
    logging.info("--- List Finished ---")

def run_download(storage):
    """Download and verify the file content."""
    logging.info("--- Running Download & Verification ---")
    try:
        logging.info(f"Reading file '{OBJECT_NAME}'...")
        download_stream = storage.download_file(BUCKET_NAME, OBJECT_NAME)
        downloaded_content = download_stream.read()
        
        # Read original file for comparison
        with open(SAMPLE_FILE_PATH, "rb") as f:
            original_content = f.read()
        
        if downloaded_content == original_content:
            logging.info(f"✅ Content verification successful. Size: {len(downloaded_content)} bytes")
        else:
            logging.error("❌ Content mismatch!")
            
    except Exception as e:
        logging.error(f"Download failed: {e}")
    logging.info("--- Download Finished ---")

def run_cleanup(storage):
    """Delete all files in the bucket, then the bucket itself."""
    logging.info("--- Running Cleanup ---")
    try:
        # 1. List all files in the bucket
        logging.info(f"Listing all files in bucket '{BUCKET_NAME}' for deletion...")
        files_to_delete = storage.list_objects(BUCKET_NAME)
        
        if not files_to_delete:
            logging.info("Bucket is already empty or does not exist.")
        else:
            # 2. Delete each file
            for object_name in files_to_delete:
                logging.info(f"Deleting file '{object_name}'...")
                storage.delete_file(BUCKET_NAME, object_name)
        
        # 3. Delete the now-empty bucket
        logging.info(f"Deleting bucket '{BUCKET_NAME}'...")
        storage.delete_bucket(BUCKET_NAME)
        
        logging.info("✅ Successfully deleted all files and the bucket.")
        
        # Optional: Check if workspace is empty
        if not os.listdir(storage.root):
            logging.info("Workspace is now empty.")
            
    except Exception as e:
        logging.error(f"Cleanup failed: {e}")
    logging.info("--- Cleanup Finished ---")

def main():
    parser = argparse.ArgumentParser(description="LocalFileSystemBackend usage example.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--setup", action="store_true", help="Initialize workspace and create bucket")
    group.add_argument("--upload", action="store_true", help="Upload sample file to bucket")
    group.add_argument("--list", action="store_true", help="List files in bucket")
    group.add_argument("--download", action="store_true", help="Download and verify file content")
    group.add_argument("--cleanup", action="store_true", help="Delete file and bucket")

    args = parser.parse_args()

    storage = get_backend()
    if not storage:
        return

    if args.setup:
        run_setup(storage)
    elif args.upload:
        run_upload(storage)
    elif args.list:
        run_list(storage)
    elif args.download:
        run_download(storage)
    elif args.cleanup:
        run_cleanup(storage)

if __name__ == "__main__":
    main()


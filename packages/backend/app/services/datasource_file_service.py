import uuid
from datetime import datetime, timezone
import os
import io
import pandas as pd
import json
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.datasource import DataSource
from app.services.minio_service import upload_bytes

def _storage_object_name(user_id: uuid.UUID, datasource_id: uuid.UUID, filename: str) -> str:
    safe_name = filename.replace("\\", "_").replace("/", "_")
    return f"datasource-files/{user_id}/{datasource_id}/{safe_name}"

def parse_file_schema(filename: str, data: bytes) -> dict:
    """Parse file to extract schema information (column names, types, first 5 rows)."""
    ext = os.path.splitext(filename.lower())[1]
    df = None
    try:
        if ext == '.csv':
            df = pd.read_csv(io.BytesIO(data), nrows=10)
        elif ext in ['.xlsx', '.xls']:
            df = pd.read_excel(io.BytesIO(data), nrows=10)
        elif ext == '.json':
            # Try to read as records, or standard json
            try:
                df = pd.read_json(io.BytesIO(data), lines=True, nrows=10)
            except Exception:
                content = json.loads(data.decode('utf-8'))
                if isinstance(content, list):
                    df = pd.DataFrame(content[:10])
                else:
                    df = pd.DataFrame([content])
        elif ext == '.parquet':
            df = pd.read_parquet(io.BytesIO(data))[:10]
        
        if df is not None:
            schema = {
                "columns": [{"name": str(col), "type": str(df[col].dtype)} for col in df.columns],
                "preview": df.head(5).to_dict(orient='records'),
                "row_count_estimate": len(df) # This is just for the preview
            }
            # Convert preview values to JSON serializable
            for row in schema["preview"]:
                for key, val in row.items():
                    if pd.isna(val):
                        row[key] = None
                    elif hasattr(val, 'isoformat'):
                        row[key] = val.isoformat()
                    elif hasattr(val, 'item'): # numpy types
                        row[key] = val.item()

            return schema
    except Exception as e:
        return {"error": str(e)}
    return {}

def create_file_datasource(
    db: Session,
    user_id: uuid.UUID,
    filename: str,
    data: bytes,
    content_type: str | None = None
) -> DataSource:
    # 1. Create record
    ds = DataSource(
        user_id=user_id,
        name=filename,
        type=os.path.splitext(filename.lower())[1].lstrip('.'),
        category="file",
        storage_path="pending",
        created_at=datetime.now(timezone.utc)
    )
    db.add(ds)
    db.commit()
    db.refresh(ds)
    
    # 2. Parse schema
    metadata = parse_file_schema(filename, data)
    ds.file_metadata = metadata
    
    # 3. Upload to MinIO
    object_name = _storage_object_name(user_id, ds.id, filename)
    upload_bytes(settings.MINIO_DATA_BUCKET, object_name, data, content_type)
    
    ds.storage_path = object_name
    db.add(ds)
    db.commit()
    db.refresh(ds)
    
    return ds

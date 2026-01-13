from __future__ import annotations

import io

from minio import Minio
from minio.error import S3Error

from app.core.config import settings


def _get_client() -> Minio:
    return Minio(
        settings.MINIO_ENDPOINT,
        access_key=settings.MINIO_ACCESS_KEY,
        secret_key=settings.MINIO_SECRET_KEY,
        secure=settings.MINIO_SECURE,
    )


def ensure_bucket(bucket_name: str) -> None:
    client = _get_client()
    if not client.bucket_exists(bucket_name):
        client.make_bucket(bucket_name)


def upload_bytes(bucket_name: str, object_name: str, data: bytes, content_type: str | None = None) -> None:
    client = _get_client()
    ensure_bucket(bucket_name)
    stream = io.BytesIO(data)
    client.put_object(
        bucket_name,
        object_name,
        data=stream,
        length=len(data),
        content_type=content_type,
    )


def download_bytes(bucket_name: str, object_name: str) -> bytes:
    client = _get_client()
    response = client.get_object(bucket_name, object_name)
    try:
        return response.read()
    finally:
        response.close()
        response.release_conn()


def delete_object(bucket_name: str, object_name: str) -> None:
    client = _get_client()
    try:
        client.remove_object(bucket_name, object_name)
    except S3Error:
        # ignore missing objects
        return

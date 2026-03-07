"""Shared datasource type/capability and filename/path helpers."""

from __future__ import annotations

import os
import re
from enum import Enum
from pathlib import Path


class DataSourceCategory(str, Enum):
    DATABASE = "database"
    FILE = "file"


class DataSourceType(str, Enum):
    POSTGRES = "postgres"
    MYSQL = "mysql"
    SQLITE = "sqlite"
    CSV = "csv"
    JSON = "json"
    XLSX = "xlsx"
    XLS = "xls"
    PARQUET = "parquet"


DATABASE_SOURCE_TYPES: set[str] = {
    DataSourceType.POSTGRES.value,
    DataSourceType.MYSQL.value,
    DataSourceType.SQLITE.value,
}

_DATASOURCE_TYPE_ALIASES: dict[str, str] = {
    "postgresql": DataSourceType.POSTGRES.value,
}

FILE_SOURCE_TYPES: set[str] = {
    DataSourceType.CSV.value,
    DataSourceType.JSON.value,
    DataSourceType.XLSX.value,
    DataSourceType.XLS.value,
    DataSourceType.PARQUET.value,
}

_SAFE_FILENAME_RE = re.compile(r"[^A-Za-z0-9._-]")


def normalize_datasource_category(category: str | None, default: str = DataSourceCategory.DATABASE.value) -> str:
    value = (category or "").strip().lower()
    if not value:
        return default
    if value not in {DataSourceCategory.DATABASE.value, DataSourceCategory.FILE.value}:
        raise ValueError(f"Unsupported datasource category: {category}")
    return value


def normalize_datasource_type(datasource_type: str | None) -> str:
    value = (datasource_type or "").strip().lower()
    value = value.lstrip(".")
    return _DATASOURCE_TYPE_ALIASES.get(value, value)


def validate_database_datasource_type(datasource_type: str | None) -> None:
    value = normalize_datasource_type(datasource_type)
    if not value:
        return
    if value not in DATABASE_SOURCE_TYPES:
        raise ValueError(f"Unsupported datasource_type: {value}")


def infer_file_type(filename: str | None) -> str:
    ext = Path((filename or "").strip()).suffix.lower().lstrip(".")
    return ext


def validate_file_type(file_type: str | None) -> None:
    value = normalize_datasource_type(file_type)
    if not value:
        raise ValueError("Unsupported file type")
    if value not in FILE_SOURCE_TYPES:
        raise ValueError(f"Unsupported file type: {value}")


def ensure_supported_filename(filename: str | None) -> str:
    ext = infer_file_type(filename)
    validate_file_type(ext)
    return ext


def sanitize_filename(filename: str | None, fallback: str = "upload") -> str:
    raw = Path((filename or "").strip()).name
    if not raw:
        raw = fallback
    safe = _SAFE_FILENAME_RE.sub("_", raw).strip("._")
    return safe or fallback


def get_datasource_filename(name: str | None, storage_path: str | None) -> str:
    if storage_path:
        base = os.path.basename(storage_path)
        if base and base != storage_path:
            return sanitize_filename(base)
    return sanitize_filename(name)


def workspace_data_path(filename: str | None) -> str:
    return f"/workspace/data/{sanitize_filename(filename)}"

"""Datasource resolution helpers for agent tasks."""

from __future__ import annotations

import uuid

from sqlalchemy import MetaData, Table, create_engine, inspect, select

from app.repositories import DataSourceRepository, SessionAttachmentRepository, SessionRepository
from app.sandbox.manager import _get_datasource_filename
from app.tasks.datasource_schema_cache import (
    build_datasource_schema_cache_key,
    get_cached_datasource_schema,
    set_cached_datasource_schema,
)
from app.tasks.db import task_session_scope
from deepeye.utils.logger import logger

_SCHEMA_PREVIEW_ROWS = 3


def get_user_id(session_id: str) -> uuid.UUID | None:
    try:
        session_uuid = uuid.UUID(session_id)
    except (TypeError, ValueError):
        return None
    with task_session_scope() as db:
        session = SessionRepository(db).get(session_uuid)
        return session.user_id if session else None


def get_session_attachment_ids(session_id: str) -> list[str]:
    try:
        session_uuid = uuid.UUID(session_id)
    except (TypeError, ValueError):
        return []
    with task_session_scope() as db:
        return SessionAttachmentRepository(db).list_datasource_ids(session_uuid)


def resolve_datasources(
    datasource_ids: list[str] | None,
    user_id: uuid.UUID | None = None,
) -> list[object]:
    if not datasource_ids:
        return []

    resolved: list[object] = []
    with task_session_scope() as db:
        repository = DataSourceRepository(db)
        for ds_id in datasource_ids:
            try:
                ds_uuid = uuid.UUID(ds_id)
            except (TypeError, ValueError):
                continue
            datasource = (
                repository.get_by_id_and_user(ds_uuid, user_id)
                if user_id
                else repository.get(ds_uuid)
            )
            if datasource:
                resolved.append(datasource)
    return resolved


def list_file_datasources(
    datasource_ids: list[str] | None,
    user_id: uuid.UUID | None = None,
) -> list[object]:
    return [
        datasource
        for datasource in resolve_datasources(datasource_ids, user_id)
        if getattr(datasource, "category", "database") == "file"
    ]


def get_datasources_info(
    datasource_ids: list[str] | None,
    user_id: uuid.UUID | None = None,
) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for datasource in resolve_datasources(datasource_ids, user_id):
        info = {
            "id": str(datasource.id),
            "name": datasource.name,
            "type": datasource.type,
            "category": getattr(datasource, "category", "database"),
        }
        if info["category"] == "file":
            original_filename = _get_datasource_filename(datasource)
            info["local_path"] = f"/workspace/data/{original_filename}"
        items.append(info)
    return items


def build_datasources_context(datasources_info: list[dict[str, str]]) -> str:
    if not datasources_info:
        return "No data sources selected."

    header = "Available Data Sources (use the file paths for workflow nodes like report.generate):"
    lines = []
    for datasource in datasources_info:
        line = f"- id: {datasource['id']}, name: {datasource['name']} ({datasource['category']})"
        if datasource["category"] == "file":
            line += f", path: {datasource.get('local_path', '')}"
        lines.append(line)
    return header + "\n" + "\n".join(lines)


def _get_database_table_preview(data_engine, table_name: str, limit: int = _SCHEMA_PREVIEW_ROWS) -> list[dict[str, object]]:
    try:
        metadata = MetaData()
        table = Table(table_name, metadata, autoload_with=data_engine)
        with data_engine.connect() as conn:
            rows = conn.execute(select(table).limit(limit)).mappings().all()
        return [dict(row) for row in rows]
    except Exception as exc:
        logger.warning("Failed to fetch preview rows for table %s: %s", table_name, exc)
        return []


def _get_single_datasource_schema(
    datasource,
    *,
    max_tables: int,
    max_columns: int,
    preview_rows: int,
) -> list[dict[str, object]]:
    cache_key = build_datasource_schema_cache_key(
        datasource,
        max_tables=max_tables,
        max_columns=max_columns,
        preview_rows=preview_rows,
    )
    cached = get_cached_datasource_schema(cache_key)
    if cached is not None:
        return cached

    category = getattr(datasource, "category", "database")
    schemas: list[dict[str, object]] = []

    if category == "database":
        connection_string = datasource.connection_string
        if not connection_string:
            return []
        try:
            from app.infra.db import json_safe_row, normalize_connection_string

            data_engine = create_engine(normalize_connection_string(connection_string))
            try:
                inspector = inspect(data_engine)
                tables = inspector.get_table_names()[:max_tables]

                for name in tables:
                    columns = inspector.get_columns(name)[:max_columns]
                    preview = _get_database_table_preview(data_engine, name, limit=preview_rows)
                    schemas.append({
                        "datasource_id": str(datasource.id),
                        "datasource_name": datasource.name,
                        "name": name,
                        "kind": "table",
                        "columns": [{"name": col.get("name"), "type": str(col.get("type"))} for col in columns],
                        "preview": [json_safe_row(dict(row)) for row in preview],
                    })
            finally:
                data_engine.dispose()
        except Exception as exc:
            logger.warning("Failed to get schema for DB %s: %s", datasource.name, exc)
            return []
    elif category == "file":
        metadata = getattr(datasource, "file_metadata", {})
        if metadata and "columns" in metadata:
            schemas.append({
                "datasource_id": str(datasource.id),
                "datasource_name": datasource.name,
                "name": datasource.name,
                "kind": "file",
                "local_path": f"/workspace/data/{_get_datasource_filename(datasource)}",
                "columns": metadata["columns"],
                "preview": (metadata.get("preview", []) or [])[:preview_rows],
            })

    set_cached_datasource_schema(cache_key, schemas)
    return schemas


def get_datasources_schema(
    datasource_ids: list[str] | None,
    user_id: uuid.UUID | None = None,
    max_tables: int = 20,
    max_columns: int = 20,
    preview_rows: int = _SCHEMA_PREVIEW_ROWS,
) -> list[dict[str, object]]:
    all_schemas: list[dict[str, object]] = []
    for datasource in resolve_datasources(datasource_ids, user_id):
        all_schemas.extend(
            _get_single_datasource_schema(
                datasource,
                max_tables=max_tables,
                max_columns=max_columns,
                preview_rows=preview_rows,
            )
        )
    return all_schemas

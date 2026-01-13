from __future__ import annotations

import re
import uuid
from datetime import date, datetime

from sqlalchemy import text


def create_engine(connection_string: str):
    from sqlalchemy import create_engine

    return create_engine(connection_string)


def validate_datasource_type(datasource_type: str | None) -> None:
    if not datasource_type:
        return
    allowed = {"postgres", "mysql", "sqlite"}
    if datasource_type not in allowed:
        raise ValueError(f"Unsupported datasource_type: {datasource_type}")


def validate_table_name(table: str) -> None:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", table):
        raise ValueError("Invalid table name")


def fetch_rows(engine, query: str, limit: int) -> list[dict]:
    with engine.connect() as conn:
        result = conn.execute(text(query))
        rows = result.mappings().fetchmany(limit)
        return [json_safe_row(dict(row)) for row in rows]


def json_safe_row(row: dict) -> dict:
    for key, value in row.items():
        if isinstance(value, (datetime, date)):
            row[key] = value.isoformat()
        elif isinstance(value, uuid.UUID):
            row[key] = str(value)
        elif hasattr(value, "quantize"):
            row[key] = float(value)
    return row

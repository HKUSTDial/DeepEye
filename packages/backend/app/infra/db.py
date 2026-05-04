from __future__ import annotations

import re
import uuid
from datetime import date, datetime

from sqlalchemy import text


def normalize_connection_string(connection_string: str) -> str:
    """Use PyMySQL driver for mysql:// URLs so MySQL works without mysqlclient (MySQLdb)."""
    s = (connection_string or "").strip()
    if s.startswith("mysql://") and not s.startswith("mysql+"):
        return "mysql+pymysql://" + s[9:]  # len("mysql://") == 9
    return s


def create_engine(connection_string: str):
    from sqlalchemy import create_engine

    url = normalize_connection_string(connection_string)
    return create_engine(url)


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

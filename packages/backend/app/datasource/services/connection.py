"""Database datasource connectivity validation helpers."""

from __future__ import annotations

from sqlalchemy import inspect, text

from app.datasource.services.specs import normalize_datasource_type, validate_database_datasource_type
from app.infra.db import create_engine, normalize_connection_string


def validate_database_connection(
    *,
    connection_string: str,
    datasource_type: str | None,
    sample_tables_limit: int = 10,
) -> dict[str, object]:
    """Validate a database connection string and return lightweight metadata."""
    ds_type = normalize_datasource_type(datasource_type)
    validate_database_datasource_type(ds_type)
    normalized_conn = normalize_connection_string((connection_string or "").strip())
    if not normalized_conn:
        raise ValueError("connection_string is required for database datasource")

    engine = create_engine(normalized_conn)
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))

        inspector = inspect(engine)
        table_names = inspector.get_table_names()
        return {
            "ok": True,
            "type": ds_type,
            "table_count": len(table_names),
            "sample_tables": table_names[:sample_tables_limit],
        }
    except Exception as exc:  # pragma: no cover - exact DB driver exceptions vary
        raise ValueError(f"Failed to connect to database: {exc}") from exc
    finally:
        engine.dispose()

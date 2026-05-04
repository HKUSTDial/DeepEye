from __future__ import annotations

import os
import sqlite3
import uuid
from pathlib import Path
from types import SimpleNamespace

import sqlalchemy

os.environ.setdefault("ALLOW_INSECURE_DEFAULTS", "true")
os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_BASE_URL", "http://localhost:8000")
os.environ.setdefault("LLM_MODEL", "test-model")

from app.tasks import agent_datasources
from app.tasks.datasource_schema_cache import clear_datasource_schema_cache
from app.datasource.services.specs import normalize_datasource_type


class _FakeSessionContext:
    def __enter__(self):
        return object()

    def __exit__(self, exc_type, exc, tb):
        return False


def test_get_datasources_schema_includes_database_preview(monkeypatch, tmp_path: Path) -> None:
    clear_datasource_schema_cache()
    db_path = tmp_path / "sales.sqlite"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE sales (client_id INTEGER, city TEXT, revenue REAL)")
    conn.executemany(
        "INSERT INTO sales (client_id, city, revenue) VALUES (?, ?, ?)",
        [
            (1, "Shanghai", 120.5),
            (2, "Hangzhou", 95.0),
            (3, "Shenzhen", 141.2),
            (4, "Beijing", 88.3),
        ],
    )
    conn.commit()
    conn.close()

    datasource_id = uuid.uuid4()
    datasource = SimpleNamespace(
        id=datasource_id,
        name="sales_db",
        type="sqlite",
        category="database",
        connection_string=f"sqlite:///{db_path}",
    )

    class _FakeDataSourceRepository:
        def __init__(self, db) -> None:
            self.db = db

        def get_by_id_and_user(self, ds_uuid, user_id):
            return datasource if ds_uuid == datasource_id else None

        def get(self, ds_uuid):
            return datasource if ds_uuid == datasource_id else None

    monkeypatch.setattr(agent_datasources, "task_session_scope", lambda: _FakeSessionContext())
    monkeypatch.setattr(agent_datasources, "DataSourceRepository", _FakeDataSourceRepository)

    schemas = agent_datasources.get_datasources_schema([str(datasource_id)], user_id=uuid.uuid4())

    assert len(schemas) == 1
    table_schema = schemas[0]
    assert table_schema["name"] == "sales"
    assert [row["city"] for row in table_schema["preview"]] == ["Shanghai", "Hangzhou", "Shenzhen"]
    assert len(table_schema["preview"]) == 3


def test_normalize_datasource_type_accepts_postgresql_alias() -> None:
    assert normalize_datasource_type("postgresql") == "postgres"
    assert normalize_datasource_type("postgres") == "postgres"


def test_get_datasources_schema_reuses_cache_for_repeated_database_requests(monkeypatch, tmp_path: Path) -> None:
    clear_datasource_schema_cache()
    db_path = tmp_path / "sales.sqlite"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE sales (client_id INTEGER, city TEXT, revenue REAL)")
    conn.execute("INSERT INTO sales (client_id, city, revenue) VALUES (1, 'Shanghai', 120.5)")
    conn.commit()
    conn.close()

    datasource_id = uuid.uuid4()
    datasource = SimpleNamespace(
        id=datasource_id,
        name="sales_db",
        type="sqlite",
        category="database",
        connection_string=f"sqlite:///{db_path}",
    )

    class _FakeDataSourceRepository:
        def __init__(self, db) -> None:
            self.db = db

        def get_by_id_and_user(self, ds_uuid, user_id):
            return datasource if ds_uuid == datasource_id else None

        def get(self, ds_uuid):
            return datasource if ds_uuid == datasource_id else None

    create_engine_calls = 0

    def _counting_create_engine(*args, **kwargs):
        nonlocal create_engine_calls
        create_engine_calls += 1
        return sqlalchemy.create_engine(*args, **kwargs)

    monkeypatch.setattr(agent_datasources, "task_session_scope", lambda: _FakeSessionContext())
    monkeypatch.setattr(agent_datasources, "DataSourceRepository", _FakeDataSourceRepository)
    monkeypatch.setattr(agent_datasources, "create_engine", _counting_create_engine)

    first = agent_datasources.get_datasources_schema([str(datasource_id)], user_id=uuid.uuid4())
    second = agent_datasources.get_datasources_schema([str(datasource_id)], user_id=uuid.uuid4())

    assert create_engine_calls == 1
    assert first == second


def test_build_datasources_context_includes_file_paths() -> None:
    context = agent_datasources.build_datasources_context(
        [
            {
                "id": "ds-1",
                "name": "sales_db",
                "type": "sqlite",
                "category": "database",
            },
            {
                "id": "ds-2",
                "name": "sales_csv",
                "type": "csv",
                "category": "file",
                "local_path": "/workspace/data/sales.csv",
            },
        ]
    )

    assert "sales_db (database)" in context
    assert "sales_csv (file), path: /workspace/data/sales.csv" in context

from __future__ import annotations

import os
import sqlite3
import uuid
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("ALLOW_INSECURE_DEFAULTS", "true")
os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_BASE_URL", "http://localhost:8000")
os.environ.setdefault("LLM_MODEL", "test-model")

from app.tasks import agent_tasks
from app.services.datasource_specs import normalize_datasource_type


class _FakeSessionContext:
    def __enter__(self):
        return object()

    def __exit__(self, exc_type, exc, tb):
        return False


class _FakeSessionFactory:
    def __call__(self):
        return _FakeSessionContext()


def test_get_datasources_schema_includes_database_preview(monkeypatch, tmp_path: Path) -> None:
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

    monkeypatch.setattr(agent_tasks, "sessionmaker", lambda bind: _FakeSessionFactory())
    monkeypatch.setattr(agent_tasks, "DataSourceRepository", _FakeDataSourceRepository)

    schemas = agent_tasks._get_datasources_schema([str(datasource_id)], user_id=uuid.uuid4())

    assert len(schemas) == 1
    table_schema = schemas[0]
    assert table_schema["name"] == "sales"
    assert [row["city"] for row in table_schema["preview"]] == ["Shanghai", "Hangzhou", "Shenzhen"]
    assert len(table_schema["preview"]) == 3


def test_normalize_datasource_type_accepts_postgresql_alias() -> None:
    assert normalize_datasource_type("postgresql") == "postgres"
    assert normalize_datasource_type("postgres") == "postgres"

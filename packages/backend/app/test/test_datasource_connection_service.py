from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.datasource.services.connection import validate_database_connection


def test_validate_database_connection_returns_table_metadata(monkeypatch) -> None:
    class DummyConn:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def execute(self, stmt):
            assert str(stmt) is not None

    class DummyEngine:
        def connect(self):
            return DummyConn()

        def dispose(self):
            return None

    monkeypatch.setattr("app.datasource.services.connection.create_engine", lambda _: DummyEngine())
    monkeypatch.setattr(
        "app.datasource.services.connection.inspect",
        lambda engine: SimpleNamespace(get_table_names=lambda: ["stores", "daily_store_sales"]),
    )

    result = validate_database_connection(
        connection_string="postgresql://user:pass@localhost:5432/db",
        datasource_type="postgresql",
    )

    assert result["ok"] is True
    assert result["type"] == "postgres"
    assert result["table_count"] == 2
    assert result["sample_tables"] == ["stores", "daily_store_sales"]


def test_validate_database_connection_surfaces_connection_errors(monkeypatch) -> None:
    class DummyEngine:
        def connect(self):
            raise RuntimeError("boom")

        def dispose(self):
            return None

    monkeypatch.setattr("app.datasource.services.connection.create_engine", lambda _: DummyEngine())

    with pytest.raises(ValueError, match="Failed to connect to database: boom"):
        validate_database_connection(
            connection_string="postgresql://user:pass@localhost:5432/db",
            datasource_type="postgres",
        )

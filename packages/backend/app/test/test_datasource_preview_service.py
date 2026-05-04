from __future__ import annotations

import sqlite3
import uuid
from types import SimpleNamespace

from app.datasource.services.preview import build_datasource_preview


def test_build_datasource_preview_paginates_csv_file(monkeypatch) -> None:
    raw_csv = b"id,name\n1,Ada\n2,Bob\n3,Cleo\n4,Dylan\n"

    monkeypatch.setattr(
        "app.datasource.services.preview.download_bytes",
        lambda bucket_name, object_name: raw_csv,
    )

    datasource = SimpleNamespace(
        id=uuid.uuid4(),
        name="customers.csv",
        type="csv",
        category="file",
        storage_path="datasource-files/u1/customers.csv",
        file_metadata={
            "columns": [
                {"name": "id", "type": "int64"},
                {"name": "name", "type": "object"},
            ]
        },
    )

    preview = build_datasource_preview(datasource=datasource, page=2, page_size=2)

    assert preview["datasource_name"] == "customers.csv"
    assert preview["category"] == "file"
    assert preview["tables"] == [{"name": "customers.csv"}]
    assert preview["table"] == "customers.csv"
    assert preview["columns"] == [
        {"name": "id", "type": "int64"},
        {"name": "name", "type": "object"},
    ]
    assert preview["rows"] == [
        {"id": "3", "name": "Cleo"},
        {"id": "4", "name": "Dylan"},
    ]
    assert preview["page"] == 2
    assert preview["page_size"] == 2
    assert preview["total_rows"] == 4
    assert preview["total_pages"] == 2


def test_build_datasource_preview_supports_database_table_switching_and_pagination(tmp_path) -> None:
    db_path = tmp_path / "preview.sqlite"
    connection = sqlite3.connect(db_path)
    try:
        connection.execute("create table customers (id integer primary key, name text)")
        connection.execute("create table orders (id integer primary key, amount real)")
        connection.executemany("insert into customers (name) values (?)", [("Ada",), ("Bob",)])
        connection.executemany("insert into orders (amount) values (?)", [(10.5,), (20.0,), (30.25,)])
        connection.commit()
    finally:
        connection.close()

    datasource = SimpleNamespace(
        id=uuid.uuid4(),
        name="analytics",
        type="sqlite",
        category="database",
        connection_string=f"sqlite:///{db_path}",
    )

    preview = build_datasource_preview(
        datasource=datasource,
        table_name="orders",
        page=2,
        page_size=2,
    )

    assert preview["datasource_name"] == "analytics"
    assert preview["category"] == "database"
    assert preview["tables"] == [{"name": "customers"}, {"name": "orders"}]
    assert preview["table"] == "orders"
    assert preview["columns"] == [
        {"name": "id", "type": "INTEGER"},
        {"name": "amount", "type": "REAL"},
    ]
    assert preview["rows"] == [{"id": 3, "amount": 30.25}]
    assert preview["page"] == 2
    assert preview["page_size"] == 2
    assert preview["total_rows"] == 3
    assert preview["total_pages"] == 2

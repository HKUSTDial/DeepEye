"""Database tools with dependency injection pattern."""

import csv
import os
import uuid
from typing import Callable

import sqlalchemy
from langchain_community.utilities import SQLDatabase

from deepeye.tools.base import tool

ARTIFACT_DIR = "artifacts"


def create_database_tools(db: SQLDatabase) -> list[Callable]:
    """
    工厂函数：为指定数据库连接创建工具集。
    使用闭包注入 db 实例，避免全局状态。
    """
    os.makedirs(ARTIFACT_DIR, exist_ok=True)

    @tool
    def list_tables() -> str:
        """List all table names in the database."""
        return ", ".join(db.get_usable_table_names())

    @tool
    def get_schema(table_names: list[str]) -> str:
        """Get schema and sample rows for specified tables."""
        return db.get_table_info(table_names)

    @tool
    def execute_sql(sql: str) -> str:
        """
        Execute SQL query.
        Returns preview and saves full result to CSV.
        """
        try:
            with db._engine.connect() as conn:
                result = conn.execute(sqlalchemy.text(sql))
                keys = list(result.keys())
                rows = result.fetchall()

            # Save to CSV
            filename = f"query_result_{uuid.uuid4().hex[:8]}.csv"
            filepath = os.path.join(ARTIFACT_DIR, filename)

            with open(filepath, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(keys)
                writer.writerows(rows)

            preview = str(rows[:5])
            return (
                f"Query Executed Successfully.\n"
                f"Full result saved to: {filepath}\n"
                f"Row Count: {len(rows)}\n"
                f"Preview: {preview}"
            )
        except Exception as e:
            return f"Error: {e}"

    return [list_tables, get_schema, execute_sql]


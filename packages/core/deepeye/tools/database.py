"""Database tools with dependency injection pattern."""

import csv
import io
import uuid
from typing import Callable

import sqlalchemy
from langchain_community.utilities import SQLDatabase

from deepeye.tools.base import tool


def create_database_tools(
    db: SQLDatabase,
    write_to_workspace: Callable[[str, str], str] | None = None,
) -> list[Callable]:
    """
    工厂函数：为指定数据库连接创建工具集。
    
    Args:
        db: SQLDatabase 实例
        write_to_workspace: 可选的回调函数，用于将文件写入 sandbox workspace
                           签名: (filename, content) -> filepath
                           如果不提供，返回结果中不包含文件路径
    """

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
        Returns preview and saves full result to CSV in /workspace.
        """
        try:
            with db._engine.connect() as conn:
                result = conn.execute(sqlalchemy.text(sql))
                keys = list(result.keys())
                rows = result.fetchall()

            # Generate CSV content
            csv_buffer = io.StringIO()
            writer = csv.writer(csv_buffer)
            writer.writerow(keys)
            writer.writerows(rows)
            csv_content = csv_buffer.getvalue()

            # Save to workspace if callback provided
            file_info = ""
            if write_to_workspace:
                filename = f"query_result_{uuid.uuid4().hex[:8]}.csv"
                filepath = write_to_workspace(filename, csv_content)
                file_info = f"Full result saved to: {filepath}\n"

            preview = str(rows[:5])
            return (
                f"Query Executed Successfully.\n"
                f"{file_info}"
                f"Row Count: {len(rows)}\n"
                f"Preview: {preview}"
            )
        except Exception as e:
            return f"Error: {e}"

    return [list_tables, get_schema, execute_sql]


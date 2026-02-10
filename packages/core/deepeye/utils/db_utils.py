"""
数据库工具函数
"""

import sqlite3
import re
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path

from deepeye.datasource.datasource import DatabaseMetadata, TableMetadata, ColumnMetadata


@dataclass
class ExecutionResult:
    """SQL执行结果"""
    result_type: str  # "success", "error", "empty_result", "all_null_result"
    result_rows: Optional[List[Tuple]] = None
    result_table_str: str = ""
    error_message: Optional[str] = None


def execute_sql(database_path: str, sql: str, timeout: int = 30) -> ExecutionResult:
    """
    执行SQL查询

    Args:
        database_path: 数据库文件路径
        sql: SQL查询语句
        timeout: 超时时间（秒）

    Returns:
        ExecutionResult: 执行结果
    """
    try:
        conn = sqlite3.connect(database_path, timeout=timeout)
        cursor = conn.cursor()
        cursor.execute(sql)
        rows = cursor.fetchall()
        column_names = [desc[0] for desc in cursor.description] if cursor.description else []
        conn.close()

        if not rows:
            return ExecutionResult(
                result_type="empty_result",
                result_rows=[],
                result_table_str="Query returned no results."
            )

        # 检查是否全为NULL
        all_null = all(all(cell is None for cell in row) for row in rows)
        if all_null:
            return ExecutionResult(
                result_type="all_null_result",
                result_rows=rows,
                result_table_str="Query returned all NULL values."
            )

        # 构建结果表字符串
        result_table_str = format_result_table(column_names, rows)

        return ExecutionResult(
            result_type="success",
            result_rows=rows,
            result_table_str=result_table_str
        )

    except Exception as e:
        return ExecutionResult(
            result_type="error",
            error_message=str(e),
            result_table_str=f"Error: {str(e)}"
        )


def format_result_table(column_names: List[str], rows: List[Tuple], max_rows: int = 10) -> str:
    """格式化结果表为字符串"""
    if not rows:
        return "Empty result"

    # 限制显示行数
    display_rows = rows[:max_rows]
    truncated = len(rows) > max_rows

    # 计算列宽
    col_widths = [len(str(name)) for name in column_names]
    for row in display_rows:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(cell) if cell is not None else "NULL"))

    # 构建表格
    lines = []
    header = " | ".join(str(name).ljust(col_widths[i]) for i, name in enumerate(column_names))
    lines.append(header)
    lines.append("-" * len(header))

    for row in display_rows:
        line = " | ".join(
            (str(cell) if cell is not None else "NULL").ljust(col_widths[i])
            for i, cell in enumerate(row)
        )
        lines.append(line)

    if truncated:
        lines.append(f"... ({len(rows) - max_rows} more rows)")

    return "\n".join(lines)


def measure_execution_time(database_path: str, sql: str) -> float:
    """测量SQL执行时间"""
    import time
    try:
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()
        start = time.time()
        cursor.execute(sql)
        cursor.fetchall()
        end = time.time()
        conn.close()
        return end - start
    except:
        return float('inf')


def get_database_schema_profile(database_schema: Dict[str, Any]) -> str:
    """
    将数据库schema转换为文本描述

    Args:
        database_schema: 数据库schema字典

    Returns:
        str: 格式化的schema描述
    """
    if not database_schema:
        return "No schema available."

    lines = []
    tables = database_schema.get("tables", {})

    for table_name, table_info in tables.items():
        lines.append(f"Table: {table_name}")

        # 表描述
        if table_info.get("description"):
            lines.append(f"  Description: {table_info['description']}")

        # 列信息
        columns = table_info.get("columns", {})
        for col_name, col_info in columns.items():
            col_type = col_info.get("column_type", "UNKNOWN")
            col_desc = col_info.get("description", "")

            col_line = f"  - {col_name} ({col_type})"
            if col_desc:
                col_line += f": {col_desc}"

            # 添加示例值
            examples = col_info.get("value_examples", [])
            if examples:
                examples_str = ", ".join(str(e) for e in examples[:5])
                col_line += f" [Value Examples: {examples_str}]"

            lines.append(col_line)

        # 主键
        pk = table_info.get("primary_key", [])
        if pk:
            lines.append(f"  Primary Key: {', '.join(pk)}")

        # 外键
        fks = table_info.get("foreign_keys", [])
        for fk in fks:
            lines.append(f"  Foreign Key: {fk['column']} -> {fk['ref_table']}.{fk['ref_column']}")

        lines.append("")

    return "\n".join(lines)


def get_database_schema_profile_from_metadata(metadata: DatabaseMetadata) -> str:
    """
    将DatabaseMetadata转换为文本描述

    Args:
        metadata: DatabaseMetadata对象

    Returns:
        str: 格式化的schema描述
    """
    lines = []

    for table in metadata.tables:
        lines.append(f"Table: {table.name}")

        if table.label:
            lines.append(f"  Label: {table.label}")
        if table.description:
            lines.append(f"  Description: {table.description}")

        for col in table.columns:
            col_line = f"  - {col.name} ({col.type})"

            if col.label:
                col_line += f" [{col.label}]"
            if col.description:
                col_line += f": {col.description}"

            # 添加示例值
            if col.examples:
                examples_str = ", ".join(str(e) for e in col.examples[:5])
                col_line += f" [Value Examples: {examples_str}]"

            # 添加枚举值
            if col.has_enums():
                enum_values = col.get_enum_values()[:5]
                col_line += f" [Enum Values: {', '.join(str(v) for v in enum_values)}]"

            lines.append(col_line)

        # 主键
        pks = table.get_primary_keys()
        if pks:
            lines.append(f"  Primary Key: {', '.join(pks)}")

        # 外键
        fks = table.get_foreign_keys()
        for fk in fks:
            if fk.ref_table:
                lines.append(f"  Foreign Key: {fk.name} -> {fk.ref_table}")

        lines.append("")

    return "\n".join(lines)


def map_lower_table_name_to_original_table_name(
        lower_table_name: str,
        database_schema: Dict[str, Any]
) -> Optional[str]:
    """
    将小写表名映射回原始表名

    Args:
        lower_table_name: 小写表名
        database_schema: 数据库schema

    Returns:
        原始表名，如果找不到返回None
    """
    tables = database_schema.get("tables", {})
    for table_name in tables.keys():
        if table_name.lower() == lower_table_name.lower():
            return table_name
    return None


def map_lower_column_name_to_original_column_name(
        table_name: str,
        lower_column_name: str,
        database_schema: Dict[str, Any]
) -> Optional[str]:
    """
    将小写列名映射回原始列名

    Args:
        table_name: 表名
        lower_column_name: 小写列名
        database_schema: 数据库schema

    Returns:
        原始列名，如果找不到返回None
    """
    tables = database_schema.get("tables", {})
    table_info = tables.get(table_name, {})
    columns = table_info.get("columns", {})

    for col_name in columns.keys():
        if col_name.lower() == lower_column_name.lower():
            return col_name
    return None


def filter_used_database_schema(
        database_schema: Dict[str, Any],
        linked_tables_and_columns: Dict[str, List[str]]
) -> Dict[str, Any]:
    """
    根据链接的表和列过滤数据库schema

    Args:
        database_schema: 完整的数据库schema
        linked_tables_and_columns: 已链接的表和列

    Returns:
        过滤后的数据库schema
    """
    filtered_schema = {"tables": {}}

    for table_name, columns in linked_tables_and_columns.items():
        if table_name in database_schema.get("tables", {}):
            original_table = database_schema["tables"][table_name]
            filtered_table = {
                "columns": {},
                "primary_key": original_table.get("primary_key", []),
                "foreign_keys": original_table.get("foreign_keys", []),
                "description": original_table.get("description", "")
            }

            for col_name in columns:
                if col_name in original_table.get("columns", {}):
                    filtered_table["columns"][col_name] = original_table["columns"][col_name]

            # 如果没有指定列，保留所有列
            if not columns:
                filtered_table["columns"] = original_table.get("columns", {})

            filtered_schema["tables"][table_name] = filtered_table

    return filtered_schema


def extract_tables_and_columns_from_sql(
        sql: str,
        database_schema: Dict[str, Any]
) -> Dict[str, List[str]]:
    """
    从SQL语句中提取表和列

    Args:
        sql: SQL语句
        database_schema: 数据库schema

    Returns:
        表和列的映射
    """
    all_table_names = list(database_schema.get("tables", {}).keys())
    all_column_names = []
    for table_name in all_table_names:
        columns = database_schema["tables"][table_name].get("columns", {})
        all_column_names.extend(columns.keys())

    all_table_names = list(set(all_table_names))
    all_column_names = list(set(all_column_names))

    sql_lower = sql.lower()

    # 匹配表名
    table_names = [
        t for t in all_table_names
        if t.lower() in sql_lower
    ]

    # 匹配列名
    column_names = [
        c for c in all_column_names
        if c.lower() in sql_lower
    ]

    used_tables_and_columns = {}
    for table_name in table_names:
        original_table_name = map_lower_table_name_to_original_table_name(table_name, database_schema)
        if original_table_name is None:
            continue

        used_tables_and_columns[original_table_name] = []

        for column_name in column_names:
            original_column_name = map_lower_column_name_to_original_column_name(
                original_table_name, column_name, database_schema
            )
            if original_column_name is not None:
                used_tables_and_columns[original_table_name].append(original_column_name)

    return used_tables_and_columns
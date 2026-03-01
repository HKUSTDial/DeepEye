"""
用于数据库的工具函数
用来连接数据库 - 执行SQL - 处理数据库的各种操作的 工具

SQL: SELECT * FROM TABLE LIMIT 3
            |
        DataBase
            |
[("张三", 26, "male"), ("李四", 28, "female")]

["姓名", "年龄", "性别"]

"""

import logging
import os
import sqlite3
import time
from typing import List, Tuple, Dict, Optional, Any
from dataclasses import dataclass
from sqlalchemy import create_engine, text


@dataclass
class ExecutionResult:
    """用于表示数据库执行SQL之后的结果"""
    result_type: str    # "success"? "error"? "empty_result"? "..."
    result_rows: Optional[List[Tuple[Any, ...]]] = None   # 记录了数据
    result_columns: Optional[List[str]] = None    # 记录了列名
    result_table_str: Optional[str] = None   # 记录了表名
    error_message: Optional[str] = None
    execution_time: float = 0.0


def _format_result_table(
        rows: List[Tuple[Any, ...]],
        columns: List[str],
        max_rows: int = 20
) -> str:
    """Format query rows into a readable plain-text table."""
    if not rows:
        return "Query returned no results"

    display_rows = rows[:max_rows]
    truncated = len(rows) > max_rows

    widths = [len(str(col)) for col in columns]
    for row in display_rows:
        for idx, value in enumerate(row):
            cell = "NULL" if value is None else str(value)
            widths[idx] = max(widths[idx], len(cell))

    header = " | ".join(str(col).ljust(widths[idx]) for idx, col in enumerate(columns))
    sep = "-+-".join("-" * widths[idx] for idx in range(len(widths)))
    lines = [header, sep]

    for row in display_rows:
        lines.append(
            " | ".join(
                ("NULL" if value is None else str(value)).ljust(widths[idx])
                for idx, value in enumerate(row)
            )
        )

    if truncated:
        lines.append(f"... ({len(rows) - max_rows} more rows)")

    return "\n".join(lines)


def _looks_like_sqlalchemy_url(value: str) -> bool:
    return "://" in value


def execute_sql(database_path: str, sql: str, timeout: float = 30.0) -> ExecutionResult:

    start_time = time.time()   # 记录开始时间

    try:
        if _looks_like_sqlalchemy_url(database_path):
            engine = create_engine(database_path)
            with engine.connect() as conn:
                result = conn.execute(text(sql))
                rows: List[Tuple] = result.fetchall()
                columns = list(result.keys()) if result.keys() is not None else []
        else:
            if not os.path.exists(database_path):
                raise FileNotFoundError(f"Database file not found: {database_path}")
            conn = sqlite3.connect(database_path, timeout=timeout)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(sql)
            rows = cursor.fetchall()
            columns = [description[0] for description in cursor.description or []]

        execution_time = time.time() - start_time

        if not rows:
            return ExecutionResult(
                result_type="empty_result",
                result_rows=[],
                result_columns=[],
                result_table_str="Query returned no results",
                execution_time=execution_time,
            )

        # 把执行结果每一行都取出来，放在 results rows 中
        results_rows = [tuple(row) for row in rows]

        # 检查是否全空
        all_null = all(all(val is None for val in row) for row in results_rows)

        result_table_str = _format_result_table(results_rows, columns)

        if not _looks_like_sqlalchemy_url(database_path):
            conn.close()

        return ExecutionResult(
            result_type="all_null_result" if all_null else "success",
            result_rows=results_rows,
            result_columns=columns,
            result_table_str=result_table_str,
            execution_time=execution_time,
        )

    except Exception as e:
        execution_time = time.time() - start_time
        error_message = str(e)
        logging.error(error_message)
        return ExecutionResult(
            result_type="error",
            result_rows=[],
            result_columns=[],
            result_table_str=error_message,
            execution_time=execution_time,
        )


if __name__ == "__main__":
    """现写现测"""
    database_path = "/Users/tiantiantian/Code/bird-2023-dataset/dev_20240627/dev_databases/card_games/card_games.sqlite"

    result = execute_sql(database_path=database_path,
                         sql="SELECT * FROM cards LIMIT 3",)







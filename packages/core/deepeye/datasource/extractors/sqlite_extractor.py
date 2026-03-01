"""
SQLite Extractor - 增强版

从SQLite数据库提取完整的元数据，包括：
- 表结构信息
- 列类型和约束
- 主键和外键
- 示例值（随机采样）
- 枚举值（对于基数较小的列）
"""

import logging
import sqlite3
import os
from typing import List, Dict, Any, Optional, Set

from deepeye.datasource.extractors.base import BaseExtractor
from deepeye.datasource.datasource import (
    DatabaseMetadata,
    TableMetadata,
    ColumnMetadata,
    EnumValueMetadata,
    ForeignKeyMetadata,
)

logger = logging.getLogger(__name__)


class SQLiteExtractor(BaseExtractor):
    """
    SQLite数据库元数据提取器

    支持提取：
    - 表名和列信息
    - 主键和外键约束
    - 示例值（随机采样）
    - 枚举值（低基数列的所有唯一值）
    """

    DB_TYPE = 'SQLite'

    def __init__(
            self,
            sample_values: bool = True,
            sample_limit: int = 10,
            enum_threshold: int = 50,
            include_views: bool = False,
            include_system_tables: bool = False,
            **kwargs
    ):
        """
        初始化SQLite提取器

        Args:
            sample_values: 是否提取示例值
            sample_limit: 示例值数量限制
            enum_threshold: 枚举值阈值，唯一值数量低于此值时提取为枚举
            include_views: 是否包含视图
            include_system_tables: 是否包含系统表
        """
        super().__init__(
            sample_values=sample_values,
            sample_limit=sample_limit,
            include_views=include_views,
            include_system_tables=include_system_tables,
        )
        self.enum_threshold = enum_threshold
        self._database_path = None

    def connect(self, database_path: str) -> sqlite3.Connection:
        """
        连接到SQLite数据库

        Args:
            database_path: 数据库文件路径

        Returns:
            数据库连接对象
        """
        if not database_path:
            raise ValueError('Database path must be provided')

        if not os.path.exists(database_path):
            raise FileNotFoundError(f'Database file not found: {database_path}')

        self._database_path = database_path
        self._connection = sqlite3.connect(database_path)
        logger.info(f"Connected to SQLite database: {database_path}")

        return self._connection

    def disconnect(self):
        """断开数据库连接"""
        if self._connection:
            self._connection.close()
            self._connection = None
            self._database_path = None
            logger.info('Disconnected from database')

    def get_database_names(self) -> str:
        """获取数据库名称（SQLite使用文件名）"""
        if self._database_path:
            return os.path.splitext(os.path.basename(self._database_path))[0]
        return "sqlite_database"

    def get_table_names(self) -> List[str]:
        """获取所有表名"""
        cursor = self._connection.cursor()

        conditions = ["type = 'table'"]

        if not self.include_system_tables:
            conditions.append("name NOT LIKE 'sqlite_%'")

        if self.include_views:
            conditions[0] = "type IN ('table', 'view')"

        query = f"SELECT name FROM sqlite_master WHERE {' AND '.join(conditions)} ORDER BY name"
        cursor.execute(query)

        return [row[0] for row in cursor.fetchall()]

    def get_columns(self, table_name: str) -> List[Dict[str, Any]]:
        """
        获取表的列信息

        Args:
            table_name: 表名

        Returns:
            列信息列表
        """
        cursor = self._connection.cursor()
        cursor.execute(f"PRAGMA table_info(`{table_name}`)")

        columns = []
        for row in cursor.fetchall():
            # row: (cid, name, type, notnull, dflt_value, pk)
            col_info = {
                "name": row[1],
                "type": row[2] or "TEXT",
                "nullable": not row[3],
                "default": row[4],
                "is_primary": bool(row[5]),
            }
            columns.append(col_info)

        return columns

    def get_primary_keys(self, table_name: str) -> List[str]:
        """获取表的主键列"""
        cursor = self._connection.cursor()
        cursor.execute(f"PRAGMA table_info(`{table_name}`)")

        pk_columns = []
        for row in cursor.fetchall():
            if row[5]:  # pk field
                pk_columns.append(row[1])

        return pk_columns

    def get_foreign_keys(self, table_name: str) -> List[Dict[str, str]]:
        """
        获取表的外键信息

        Returns:
            外键列表，每个外键包含: from_column, to_table, to_column
        """
        cursor = self._connection.cursor()
        cursor.execute(f"PRAGMA foreign_key_list(`{table_name}`)")

        foreign_keys = []
        for row in cursor.fetchall():
            # row: (id, seq, table, from, to, on_update, on_delete, match)
            fk_info = {
                "from_column": row[3],
                "to_table": row[2],
                "to_column": row[4],
            }
            foreign_keys.append(fk_info)

        return foreign_keys

    def get_sample_values(
            self,
            table_name: str,
            column_name: str,
            limit: int = None
    ) -> List[Any]:
        """
        获取列的示例值（随机采样）

        Args:
            table_name: 表名
            column_name: 列名
            limit: 采样数量限制

        Returns:
            示例值列表
        """
        if limit is None:
            limit = self.sample_limit

        cursor = self._connection.cursor()

        try:
            # 使用RANDOM()进行随机采样，排除NULL值
            query = f"""
                SELECT DISTINCT `{column_name}` 
                FROM `{table_name}` 
                WHERE `{column_name}` IS NOT NULL 
                ORDER BY RANDOM() 
                LIMIT {limit}
            """
            cursor.execute(query)
            return [row[0] for row in cursor.fetchall()]

        except Exception as e:
            logger.warning(f"Failed to get sample values for {table_name}.{column_name}: {e}")
            return []

    def get_column_distinct_count(self, table_name: str, column_name: str) -> int:
        """
        获取列的唯一值数量

        Args:
            table_name: 表名
            column_name: 列名

        Returns:
            唯一值数量
        """
        cursor = self._connection.cursor()

        try:
            query = f"SELECT COUNT(DISTINCT `{column_name}`) FROM `{table_name}`"
            cursor.execute(query)
            result = cursor.fetchone()
            return result[0] if result else 0

        except Exception as e:
            logger.warning(f"Failed to get distinct count for {table_name}.{column_name}: {e}")
            return 0

    def get_enum_values(
            self,
            table_name: str,
            column_name: str,
            limit: int = None
    ) -> List[Any]:
        """
        获取列的枚举值（低基数列的所有唯一值）

        Args:
            table_name: 表名
            column_name: 列名
            limit: 枚举值数量限制

        Returns:
            枚举值列表
        """
        if limit is None:
            limit = self.enum_threshold

        # 先检查唯一值数量
        distinct_count = self.get_column_distinct_count(table_name, column_name)

        # 如果唯一值数量超过阈值，不作为枚举
        if distinct_count > self.enum_threshold:
            return []

        cursor = self._connection.cursor()

        try:
            query = f"""
                SELECT DISTINCT `{column_name}` 
                FROM `{table_name}` 
                WHERE `{column_name}` IS NOT NULL 
                ORDER BY `{column_name}` 
                LIMIT {limit}
            """
            cursor.execute(query)
            return [row[0] for row in cursor.fetchall()]

        except Exception as e:
            logger.warning(f"Failed to get enum values for {table_name}.{column_name}: {e}")
            return []

    def extract_table_metadata(self, table_name: str) -> TableMetadata:
        """
        提取单个表的完整元数据

        Args:
            table_name: 表名

        Returns:
            表元数据对象
        """
        # 获取列信息
        columns_info = self.get_columns(table_name)

        # 获取主键
        primary_keys = set(self.get_primary_keys(table_name))

        # 获取外键
        foreign_keys = self.get_foreign_keys(table_name)
        fk_columns = {fk["from_column"] for fk in foreign_keys}

        columns = []
        for col_info in columns_info:
            col_name = col_info["name"]
            col_type = col_info["type"]

            # 创建列元数据
            column = ColumnMetadata(
                name=col_name,
                type=col_type,
                is_primary=col_name in primary_keys,
                is_foreign=col_name in fk_columns,
            )

            # 提取示例值
            if self.sample_values:
                examples = self.get_sample_values(table_name, col_name)
                column.examples = examples

            # 提取枚举值（仅对TEXT类型的列）
            col_type_upper = col_type.upper()
            if "TEXT" in col_type_upper or "VARCHAR" in col_type_upper or "CHAR" in col_type_upper:
                enum_values = self.get_enum_values(table_name, col_name)
                if enum_values:
                    column.enums = [
                        EnumValueMetadata(value=v) for v in enum_values
                    ]

            columns.append(column)

        # 创建表元数据
        table = TableMetadata(
            name=table_name,
            columns=columns,
            foreign_keys=[
                ForeignKeyMetadata(
                    name=fk["from_column"],
                    ref_table=fk.get("to_table"),
                    ref_column=fk.get("to_column"),
                )
                for fk in foreign_keys
            ],
        )

        return table

    def extract(self) -> DatabaseMetadata:
        """
        提取完整的数据库元数据

        Returns:
            数据库元数据对象
        """
        if self._connection is None:
            raise ConnectionError("No database connection. Call connect() first.")

        db_name = self.get_database_names()
        table_names = self.get_table_names()

        logger.info(f"Extracting metadata for {len(table_names)} tables...")

        tables = []
        for i, table_name in enumerate(table_names):
            try:
                table = self.extract_table_metadata(table_name)
                tables.append(table)
                logger.debug(f"Extracted metadata for table: {table_name} ({i + 1}/{len(table_names)})")
            except Exception as e:
                logger.error(f"Failed to extract metadata for table {table_name}: {e}")
                continue

        metadata = DatabaseMetadata(
            name=db_name,
            db_type=self.DB_TYPE,
            tables=tables,
        )

        logger.info(f"Successfully extracted metadata: {len(tables)} tables")

        return metadata

    def get_table_row_count(self, table_name: str) -> int:
        """获取表的行数"""
        cursor = self._connection.cursor()

        try:
            cursor.execute(f"SELECT COUNT(*) FROM `{table_name}`")
            result = cursor.fetchone()
            return result[0] if result else 0
        except Exception as e:
            logger.warning(f"Failed to get row count for {table_name}: {e}")
            return 0

    def get_table_statistics(self, table_name: str) -> Dict[str, Any]:
        """
        获取表的统计信息

        Returns:
            包含行数、列数等统计信息的字典
        """
        columns = self.get_columns(table_name)
        row_count = self.get_table_row_count(table_name)

        return {
            "table_name": table_name,
            "row_count": row_count,
            "column_count": len(columns),
            "columns": [c["name"] for c in columns],
        }


if __name__ == '__main__':
    # 测试代码
    import json

    extractor = SQLiteExtractor(
        sample_values=True,
        sample_limit=5,
        enum_threshold=20,
    )

    # 替换为实际的数据库路径
    db_path = '/Users/tiantiantian/Code/bird-2023-dataset/dev_20240627/dev_databases/card_games/card_games.sqlite'

    if os.path.exists(db_path):
        extractor.connect(database_path=db_path)
        metadata = extractor.extract()

        # 打印提取的元数据
        for table in metadata.tables:
            print(f"\nTable: {table.name}")
            for col in table.columns:
                print(f"  Column: {col.name} ({col.type})")
                if col.examples:
                    print(f"    Examples: {col.examples[:3]}")
                if col.enums:
                    enum_values = [e.value for e in col.enums[:5]]
                    print(f"    Enums: {enum_values}")

        extractor.disconnect()
    else:
        print(f"Database not found: {db_path}")

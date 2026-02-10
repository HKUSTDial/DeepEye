"""
SQLAlchemy Extractor - Generic extractor for SQL databases.

Supports:
- PostgreSQL
- MySQL
- SQLite (via SQLAlchemy URL)
"""

import logging
from typing import List, Dict, Any

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy import inspect

from deepeye.datasource.extractors.base import BaseExtractor
from deepeye.datasource.datasource import (
    DatabaseMetadata,
    TableMetadata,
    ColumnMetadata,
    EnumValueMetadata,
    ForeignKeyMetadata,
)

logger = logging.getLogger(__name__)


class SQLAlchemyExtractor(BaseExtractor):
    """
    SQLAlchemy database metadata extractor.
    """

    DB_TYPE = "SQLAlchemy"

    def __init__(
        self,
        sample_values: bool = True,
        sample_limit: int = 10,
        enum_threshold: int = 50,
        include_views: bool = False,
        include_system_tables: bool = False,
        **kwargs,
    ):
        super().__init__(
            sample_values=sample_values,
            sample_limit=sample_limit,
            include_views=include_views,
            include_system_tables=include_system_tables,
        )
        self.enum_threshold = enum_threshold
        self._engine: Engine | None = None

    def connect(self, connection_string: str) -> Engine:
        if not connection_string:
            raise ValueError("connection_string must be provided")
        self._engine = create_engine(connection_string)
        logger.info("Connected to database via SQLAlchemy")
        return self._engine

    def disconnect(self):
        if self._engine:
            self._engine.dispose()
            self._engine = None
            logger.info("Disconnected from database")

    def _get_inspector(self):
        if not self._engine:
            raise ConnectionError("No database connection. Call connect() first.")
        return inspect(self._engine)

    def get_database_names(self) -> str:
        if not self._engine:
            return "database"
        return self._engine.url.database or "database"

    def get_table_names(self) -> List[str]:
        inspector = self._get_inspector()
        tables = inspector.get_table_names()
        if self.include_views:
            tables += inspector.get_view_names()
        if not self.include_system_tables:
            tables = [t for t in tables if not t.startswith("sqlite_")]
        return sorted(set(tables))

    def get_columns(self, table_name: str) -> List[Dict[str, Any]]:
        inspector = self._get_inspector()
        columns = inspector.get_columns(table_name)
        return [
            {
                "name": col.get("name"),
                "type": str(col.get("type") or "TEXT"),
                "nullable": col.get("nullable", True),
                "default": col.get("default"),
            }
            for col in columns
        ]

    def _get_primary_keys(self, table_name: str) -> List[str]:
        inspector = self._get_inspector()
        pk = inspector.get_pk_constraint(table_name) or {}
        return list(pk.get("constrained_columns") or [])

    def _get_foreign_keys(self, table_name: str) -> List[Dict[str, str]]:
        inspector = self._get_inspector()
        foreign_keys = []
        for fk in inspector.get_foreign_keys(table_name) or []:
            constrained = fk.get("constrained_columns") or []
            referred_table = fk.get("referred_table")
            referred_columns = fk.get("referred_columns") or []
            for idx, col in enumerate(constrained):
                foreign_keys.append(
                    {
                        "from_column": col,
                        "to_table": referred_table,
                        "to_column": referred_columns[idx] if idx < len(referred_columns) else None,
                    }
                )
        return foreign_keys

    def _quote_ident(self, name: str) -> str:
        if not self._engine:
            return name
        return self._engine.dialect.identifier_preparer.quote(name)

    def get_sample_values(self, table_name: str, column_name: str, limit: int = None) -> List[Any]:
        if limit is None:
            limit = self.sample_limit
        if not self._engine:
            return []
        q_table = self._quote_ident(table_name)
        q_col = self._quote_ident(column_name)
        sql = text(
            f"SELECT DISTINCT {q_col} FROM {q_table} "
            f"WHERE {q_col} IS NOT NULL LIMIT :limit"
        )
        try:
            with self._engine.connect() as conn:
                rows = conn.execute(sql, {"limit": limit}).fetchall()
            return [row[0] for row in rows]
        except Exception as exc:
            logger.warning(f"Failed to get sample values for {table_name}.{column_name}: {exc}")
            return []

    def _get_distinct_count(self, table_name: str, column_name: str) -> int:
        if not self._engine:
            return 0
        q_table = self._quote_ident(table_name)
        q_col = self._quote_ident(column_name)
        sql = text(f"SELECT COUNT(DISTINCT {q_col}) FROM {q_table}")
        try:
            with self._engine.connect() as conn:
                result = conn.execute(sql).scalar()
            return int(result or 0)
        except Exception as exc:
            logger.warning(f"Failed to get distinct count for {table_name}.{column_name}: {exc}")
            return 0

    def _get_enum_values(self, table_name: str, column_name: str, limit: int = None) -> List[Any]:
        if limit is None:
            limit = self.enum_threshold
        distinct_count = self._get_distinct_count(table_name, column_name)
        if distinct_count > self.enum_threshold:
            return []
        if not self._engine:
            return []
        q_table = self._quote_ident(table_name)
        q_col = self._quote_ident(column_name)
        sql = text(
            f"SELECT DISTINCT {q_col} FROM {q_table} "
            f"WHERE {q_col} IS NOT NULL ORDER BY {q_col} LIMIT :limit"
        )
        try:
            with self._engine.connect() as conn:
                rows = conn.execute(sql, {"limit": limit}).fetchall()
            return [row[0] for row in rows]
        except Exception as exc:
            logger.warning(f"Failed to get enum values for {table_name}.{column_name}: {exc}")
            return []

    def extract_table_metadata(self, table_name: str) -> TableMetadata:
        columns_info = self.get_columns(table_name)
        primary_keys = set(self._get_primary_keys(table_name))
        foreign_keys = self._get_foreign_keys(table_name)
        fk_columns = {fk["from_column"] for fk in foreign_keys}

        columns: List[ColumnMetadata] = []
        for col_info in columns_info:
            col_name = col_info.get("name")
            col_type = col_info.get("type") or "TEXT"
            column = ColumnMetadata(
                name=col_name,
                type=col_type,
                is_primary=col_name in primary_keys,
                is_foreign=col_name in fk_columns,
            )

            if self.sample_values:
                column.examples = self.get_sample_values(table_name, col_name)

            col_type_upper = str(col_type).upper()
            if "TEXT" in col_type_upper or "VARCHAR" in col_type_upper or "CHAR" in col_type_upper:
                enum_values = self._get_enum_values(table_name, col_name)
                if enum_values:
                    column.enums = [EnumValueMetadata(value=v) for v in enum_values]

            columns.append(column)

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
        if not self._engine:
            raise ConnectionError("No database connection. Call connect() first.")
        tables = []
        for table_name in self.get_table_names():
            try:
                tables.append(self.extract_table_metadata(table_name))
            except Exception as exc:
                logger.warning(f"Failed to extract metadata for {table_name}: {exc}")
                continue
        return DatabaseMetadata(
            name=self.get_database_names(),
            db_type=str(self._engine.url.get_backend_name() if self._engine else "database"),
            tables=tables,
        )

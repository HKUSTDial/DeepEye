"""
将 各类数据库的结构，抽象成为 DataSource
"""

import uuid
from typing import List, Optional, Dict, Any, Set, Union
from datetime import datetime, timezone
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict, field_validator


class EnumValueMetadata(BaseModel):
    """
    枚举值元数据 用于描述字段的可选值
    """
    model_config = ConfigDict(validate_assignment=True)
    id: str = Field(default_factory=lambda: str(uuid.uuid4()).replace('-', '')[:8], description='枚举值唯一标识')
    value: Any = Field(..., description="枚举值(实际存储的值)")

    def __str__(self) -> str:
        return self.value


class ForeignKeyMetadata(BaseModel):
    """外键元数据"""
    model_config = ConfigDict(validate_assignment=True)
    name: str = Field(..., description="外键列名")
    ref_table: Optional[str] = Field(None, description="引用表名")
    ref_column: Optional[str] = Field(None, description="引用列名")


class ColumnMetadata(BaseModel):
    """ 列元数据 """
    model_config = ConfigDict(validate_assignment=True)

    name: str = Field(..., description="字段英文名(实际列名)")
    type: str = Field(default="VARCHAR(256)", description="字段类型")
    label: Optional[str] = Field(None, description="字段中文名/别名")
    description: Optional[str] = Field(None, description="字段描述")
    is_primary: bool = Field(False, description="是否为主键")
    is_foreign: bool = Field(False, description="是否为外键")
    enums: List[EnumValueMetadata] = Field([], description="字段的枚举值,可以是EnumValueMetadata对象列表或简单值列表")
    examples: List[Any] = Field([], description="这个列里面的示例数据（随机采出来）")

    def has_enums(self) -> bool:
        return bool(self.enums)

    def get_enum_values(self) -> List[Any]:
        values: List[Any] = []
        for enum in self.enums:
            if hasattr(enum, "value"):
                values.append(enum.value)
            else:
                values.append(enum)
        return values


class TableMetadata(BaseModel):
    """表元数据"""
    model_config = ConfigDict(validate_assignment=True)
    id: str = Field(default_factory=lambda: str(uuid.uuid4()).replace('-', '')[:8], description="表的唯一标识")
    name: str = Field(..., description="表英文名(实际表名)")
    label: Optional[str] = Field(None, description="表中文名/别名")
    description: Optional[str] = Field(None, description="表描述")
    columns: List[ColumnMetadata] = Field(default_factory=list, description="列列表")
    foreign_keys: List[ForeignKeyMetadata] = Field(default_factory=list, description="外键信息列表")

    def get_primary_keys(self) -> List[str]:
        return [col.name for col in self.columns if getattr(col, "is_primary", False)]

    def get_foreign_keys(self) -> List[ForeignKeyMetadata]:
        return list(self.foreign_keys)


class DatabaseMetadata(BaseModel):
    """数据库元数据顶层数据结构"""
    model_config = ConfigDict(validate_assignment=True)

    id: str = Field(default_factory=lambda: str(uuid.uuid4()).replace('-', ''), description="数据源唯一标识标识")

    name: str = Field(..., description="数据库名称")

    db_type: str = Field(..., description="数据库类型")
    db_version: Optional[str] = Field(None, description="数据库版本")

    tables: List[TableMetadata] = Field(
        default_factory=list,
        description="表列表(扁平结构)"
    )

    def get_table(self, table_name: str) -> Optional[TableMetadata]:
        for table in self.tables:
            if table.name == table_name:
                return table
        return None


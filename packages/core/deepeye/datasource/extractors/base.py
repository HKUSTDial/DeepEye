"""
用于建立 真实的数据库（如 Sqlite, Mysql, Oracle等数据库） 将他们 转换为 DataBaseMetaData 这个数据结构


数据库 -> DataSource -> Value Retrival -> Schema Linking -> ....
"""


from deepeye.datasource.datasource import (DatabaseMetadata,
                                           TableMetadata,
                                           ColumnMetadata)

from abc import ABC, abstractmethod
from typing import List, Tuple, Dict, Any

from deepeye.utils.logger import logger


class BaseExtractor(ABC):

    DB_TYPE = 'UNKNOWN'

    def __init__(self,
                 sample_values: bool = True,   # 是否有数据在Datasource中
                 sample_limit: int = 10,
                 include_views: bool = False,
                 include_system_tables: bool = False,):

        self.sample_values = sample_values
        self.sample_limit = sample_limit
        self.include_views = include_views
        self.include_system_tables = include_system_tables

        self._connection = None   # 数据库的连接器

    @abstractmethod
    def connect(self, **kwargs) -> Any:
        raise NotImplementedError

    @abstractmethod
    def disconnect(self) -> Any:
        pass

    @abstractmethod
    def get_database_names(self) -> str:
        """
        获取数据库的名字
        """
        raise NotImplementedError

    @abstractmethod
    def get_table_names(self) -> List[str]:
        raise NotImplementedError

    @abstractmethod
    def get_columns(self, table_name: str) -> List[Dict[str, Any]]:
        """
        输出需要保持格式为：
        [{"name": "xxxx", "type": "xxx"}]

        """
        raise NotImplementedError

    def get_sample_values(self,
                          table_name: str,
                          column_name: str,
                          limit: int = 10) -> List[Any]:
        """
        获取某个表、某个列的枚举值
        """
        return []

    def extract_table_metadata(self, table_name: str) -> TableMetadata:
        """将某个指定的数据表的信息进行抽取"""

        columns_info = self.get_columns(table_name)

        columns = []

        for column_info in columns_info:

            col_name = column_info['name']
            col_type = column_info['type']

            column = ColumnMetadata(name=col_name, type=col_type)

            columns.append(column)

        table = TableMetadata(name=table_name, columns=columns)

        return table

    def extract(self) -> DatabaseMetadata:
        """
        总的方法
        """

        if self._connection is None:
            raise ConnectionError("No database connection")

        db_names = self.get_database_names()   # 获取到数据库的名字
        table_names = self.get_table_names()   # 获取到数据库中所有表的名字

        # 构建数据表的元信息
        tables = []
        for table_name in table_names:   # 针对每一个表名，我们提取该表的元数据
            try:
                table: TableMetadata = self.extract_table_metadata(table_name)
                tables.append(table)
            except Exception as e:
                logger.error(e)
                continue

        # 构建数据库的元信息
        metadata = DatabaseMetadata(tables=tables,
                                    name=db_names,
                                    db_type=self.DB_TYPE)  # 数据库的类型，如Sqlite，MySQL

        return metadata



















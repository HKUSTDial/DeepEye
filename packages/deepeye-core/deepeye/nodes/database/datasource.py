"""数据库数据源节点

统一的数据库数据源，支持两种模式：
1. 内省模式：提取 schema 信息，用于驱动 NL2SQL
2. 查询模式：执行指定的 SQL，返回 DataFrame 结果
"""

from typing import Optional, List, Dict, Any
from enum import Enum
import pandas as pd

from deepeye.nodes.base import NodeMetadata
from deepeye.nodes.datasource.base import BaseDataSourceNode, DataSourceConfig
from deepeye.nodes.database.connection import DatabaseConnection
from deepeye.nodes.io import (
    NodeInput,
    NodeOutput,
    NodeInputPort,
    NodeInputSchema,
    NodeOutputPort,
    NodeOutputSchema,
)


class DatabaseSourceMode(str, Enum):
    """数据库数据源工作模式"""
    INTROSPECT = "introspect"  # 内省模式：提取 schema 信息
    QUERY = "query"            # 查询模式：执行 SQL 查询


class DatabaseDataSourceConfig(DataSourceConfig):
    """数据库数据源配置
    
    Attributes:
        connection_string: 数据库连接字符串
            - SQLite: "sqlite:///path/to/db.db"
            - MySQL: "mysql+pymysql://user:pass@host:port/dbname"
            - PostgreSQL: "postgresql://user:pass@host:port/dbname"
        
        mode: 工作模式
            - INTROSPECT: 内省模式，提取 schema 信息
            - QUERY: 查询模式，执行 SQL 查询
        
        # 内省模式配置
        tables: 要内省的表名列表（None 表示所有表）
        sample_size: 每个列的示例值数量
        max_value_length: 示例值的最大字符串长度（避免 Prompt 过大）
        include_statistics: 是否包含统计信息（行数、唯一值等）
        
        # 通用配置
        max_rows: 查询结果的最大行数限制
        timeout: 查询超时时间（秒）
    """
    
    connection_string: str
    mode: DatabaseSourceMode = DatabaseSourceMode.INTROSPECT
    
    # 内省模式配置
    tables: Optional[List[str]] = None
    sample_size: int = 5
    max_value_length: int = 100
    include_statistics: bool = True
    
    # 通用配置
    max_rows: int = 100000
    timeout: int = 60


class DatabaseDataSourceNode(BaseDataSourceNode):
    """数据库数据源节点
    
    统一的数据库数据源，支持两种工作模式：
    
    模式 1: Schema 内省模式 (INTROSPECT)
        - 自动提取数据库 schema、示例数据、统计信息
        - 输出包含 connection_string 和 database_info
        - 用于驱动 NL2SQL 节点
    
    模式 2: 直接查询模式 (QUERY)
        - 执行指定的 SQL 查询
        - 通过 sql 输入端口接收 SQL 查询
        - 输出 DataFrame 结果
        - 用于直接数据获取场景
    
    输出端口:
        - data: 统一的数据输出端口
            - 内省模式: 输出包含 connection_string 和 database_info 的字典
            - 查询模式: 输出 DataFrame 查询结果
    
    输入端口 (仅查询模式):
        - sql: SQL 查询语句
    
    Examples:
        >>> # 模式 1: 内省模式（配合 NL2SQL）
        >>> db_source = DatabaseDataSourceNode(
        ...     node_id="db_introspect",
        ...     config={
        ...         "connection_string": "sqlite:///sales.db",
        ...         "mode": "introspect",
        ...         "sample_size": 10
        ...     }
        ... )
        >>> outputs = db_source.run({})
        >>> result = outputs["data"].data
        >>> print(result["connection_string"])  # "sqlite:///sales.db"
        >>> print(result["database_info"]["schema"]["tables"])  # ['products', 'orders']
        
        >>> # 模式 2: 直接查询模式
        >>> db_query = DatabaseDataSourceNode(
        ...     node_id="db_query",
        ...     config={
        ...         "connection_string": "sqlite:///sales.db",
        ...         "mode": "query"
        ...     }
        ... )
        >>> outputs = db_query.run({
        ...     "sql": NodeInput(data="SELECT * FROM products WHERE price > 100")
        ... })
        >>> df = outputs["data"].data["dataframe"]
        >>> print(df.head())
    """
    
    node_type = "DatabaseDataSource"
    
    def __init__(
        self,
        node_id: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        """初始化数据库数据源节点
        
        Args:
            node_id: 节点实例ID
            config: 节点配置字典
        
        Raises:
            ValueError: 配置无效
        """
        super().__init__(node_id, config)
        
        # 设置节点元数据
        self.metadata = NodeMetadata(
            name="DatabaseDataSource",
            display_name="数据库数据源",
            description="从数据库读取数据或提取 schema 信息（支持 SQLite、MySQL、PostgreSQL）",
            category="datasource",
            tags=["database", "sql", "sqlite", "mysql", "postgresql"],
            version="0.1.0",
            author="DeepEye"
        )
        
        # 创建数据库连接
        self.db_connection: Optional[DatabaseConnection] = None
        
        # 根据模式设置端口
        self._setup_ports()
    
    def _parse_config(self, config: Dict[str, Any]) -> DatabaseDataSourceConfig:
        """解析配置
        
        Args:
            config: 配置字典
        
        Returns:
            DatabaseDataSourceConfig 对象
        """
        return DatabaseDataSourceConfig(**config)
    
    def _setup_ports(self):
        """根据工作模式设置输入和输出端口"""
        # 输出端口：无论哪种模式都是 data，但 schema 不同
        if self.config.mode == DatabaseSourceMode.INTROSPECT:
            # 内省模式：输出包含 connection_string 和 database_info 的字典
            self.output_ports = [
                NodeOutputPort(
                    name="data",
                    label="数据输出",
                    schemas=[
                        NodeOutputSchema(
                            name="connection_string",
                            type="string",
                            description="数据库连接字符串（传递给下游节点）"
                        ),
                        NodeOutputSchema(
                            name="database_info",
                            type="object",
                            description="数据库 schema、示例数据、统计信息"
                        )
                    ]
                )
            ]
            # 内省模式没有输入端口
            self.input_ports = []
        else:
            # 查询模式：输出 DataFrame
            self.output_ports = [
                NodeOutputPort(
                    name="data",
                    label="查询结果",
                    schemas=[
                        NodeOutputSchema(
                            name="dataframe",
                            type="object",
                            description="SQL 查询结果（DataFrame）"
                        )
                    ]
                )
            ]
            # 查询模式有 SQL 输入端口
            self.input_ports = [
                NodeInputPort(
                    name="sql",
                    label="SQL 查询",
                    schemas=[
                        NodeInputSchema(
                            name="sql",
                            type="string",
                            description="SQL 查询语句",
                            required=True
                        )
                    ]
                )
            ]
    
    def _get_db_connection(self) -> DatabaseConnection:
        """获取或创建数据库连接
        
        Returns:
            DatabaseConnection 对象
        """
        if self.db_connection is None:
            self.db_connection = DatabaseConnection(
                self.config.connection_string
            )
        return self.db_connection
    
    def _load_data(self) -> pd.DataFrame:
        """加载数据（查询模式）
        
        这个方法在查询模式下被调用，不应该被直接使用。
        查询模式下应该通过 execute 方法处理。
        
        Returns:
            空 DataFrame（内省模式）
        """
        # 内省模式返回空 DataFrame
        # 实际数据由 execute 方法直接处理
        return pd.DataFrame()
    
    def _introspect_database(self) -> Dict[str, Any]:
        """数据库内省（内省模式）
        
        提取数据库的 schema、示例数据、统计信息。
        
        Returns:
            数据库信息字典: {
                "schema": {...},
                "examples": {...},
                "statistics": {...}
            }
        """
        db = self._get_db_connection()
        
        # 1. 获取 schema 信息
        schema_info = db.get_schema_info(tables=self.config.tables)
        
        # 2. 获取示例数据（非重复、非 NULL、按长度排序、有长度限制）
        examples = db.get_sample_data(
            tables=self.config.tables,
            sample_size=self.config.sample_size,
            max_value_length=self.config.max_value_length
        )
        
        # 3. 获取统计信息（可选）
        statistics = {}
        if self.config.include_statistics:
            statistics = db.get_table_statistics(tables=self.config.tables)
        
        return {
            "schema": schema_info,
            "examples": examples,
            "statistics": statistics,
            "dialect": db.dialect,  # 数据库类型（sqlite, mysql, postgresql）
        }
    
    def execute(self, inputs: Dict[str, NodeInput]) -> Dict[str, NodeOutput]:
        """执行数据源节点
        
        根据配置的模式（内省/查询）执行不同的逻辑。
        
        Args:
            inputs: 输入数据
                - 内省模式: 无输入
                - 查询模式: {"sql": SQL 查询语句}
        
        Returns:
            输出字典: {"data": NodeOutput}
                - 内省模式: data 包含 {"connection_string": ..., "database_info": ...}
                - 查询模式: data 包含 DataFrame
        """
        try:
            # 测试连接
            db = self._get_db_connection()
            if not db.test_connection():
                raise ConnectionError(f"无法连接到数据库: {self.config.connection_string}")
            
            if self.config.mode == DatabaseSourceMode.INTROSPECT:
                # 内省模式
                return self._execute_introspect_mode()
            else:
                # 查询模式
                return self._execute_query_mode(inputs)
        
        except Exception as e:
            # 统一的错误处理
            error_output = NodeOutput(
                data=None,
                error=str(e),  # 使用 error 字段而不是 metadata
                status="failed"  # 使用 failed 状态
            )
            return {"data": error_output}
    
    def _execute_introspect_mode(self) -> Dict[str, NodeOutput]:
        """执行内省模式
        
        Returns:
            输出字典: {"data": {...}}
                data 包含 connection_string 和 database_info
        """
        # 执行内省
        database_info = self._introspect_database()
        
        # 构建输出数据（包含 connection_string 和 database_info）
        output_data = {
            "connection_string": self.config.connection_string,
            "database_info": database_info
        }
        
        # 构建元数据
        metadata = {
            "mode": "introspect",
            "tables": database_info["schema"]["tables"],
            "total_tables": len(database_info["schema"]["tables"]),
            "dialect": database_info["dialect"],
        }
        
        return {
            "data": NodeOutput(
                data=output_data,
                metadata=metadata,
                status="success"
            )
        }
    
    def _execute_query_mode(self, inputs: Dict[str, NodeInput]) -> Dict[str, NodeOutput]:
        """执行查询模式
        
        Args:
            inputs: 输入数据，必须包含 "sql" 键
        
        Returns:
            输出字典: {"data": {"dataframe": DataFrame}}
        """
        # 获取 SQL 查询语句
        if "sql" not in inputs:
            raise ValueError("查询模式需要提供 'sql' 输入")
        
        sql = inputs["sql"].data
        if not sql or not isinstance(sql, str):
            raise ValueError("SQL 查询必须是非空字符串")
        
        # 执行查询
        db = self._get_db_connection()
        try:
            df = db.execute_query(sql)
            
            # 应用行数限制
            if len(df) > self.config.max_rows:
                df = df.head(self.config.max_rows)
        except Exception as e:
            raise ValueError(f"SQL 查询执行失败: {e}")
        
        # 构建输出数据（符合 OutputSchema 定义）
        output_data = {
            "dataframe": df
        }
        
        # 构建元数据
        metadata = self._build_metadata(df)
        metadata["mode"] = "query"
        metadata["sql"] = sql
        
        return {
            "data": NodeOutput(
                data=output_data,
                metadata=metadata,
                status="success"
            )
        }
    
    def _get_source_info(self) -> Dict[str, Any]:
        """获取数据源特定信息
        
        Returns:
            数据源信息字典
        """
        db = self._get_db_connection()
        return {
            "connection_string": self.config.connection_string,
            "dialect": db.dialect if db else "unknown",
            "mode": self.config.mode.value,  # 使用 mode 枚举的值
        }
    
    def __del__(self):
        """析构函数：关闭数据库连接"""
        if self.db_connection:
            try:
                self.db_connection.close()
            except:
                pass



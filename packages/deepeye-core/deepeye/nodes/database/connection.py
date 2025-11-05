"""数据库连接管理

提供统一的数据库连接抽象，支持：
- SQLite
- MySQL
- PostgreSQL
- 其他 SQLAlchemy 支持的数据库
"""

from typing import Any, Dict, Optional, List
from contextlib import contextmanager
import sqlalchemy as sa
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine, Connection
from urllib.parse import urlparse
import pandas as pd


class DatabaseConnection:
    """数据库连接管理器
    
    封装 SQLAlchemy 引擎，提供统一的数据库操作接口。
    
    Attributes:
        connection_string: 数据库连接字符串
        engine: SQLAlchemy Engine 对象
        dialect: 数据库方言（sqlite, mysql, postgresql 等）
    
    Examples:
        >>> # SQLite
        >>> db = DatabaseConnection("sqlite:///sales.db")
        >>> 
        >>> # MySQL
        >>> db = DatabaseConnection("mysql+pymysql://user:pass@localhost/mydb")
        >>> 
        >>> # PostgreSQL
        >>> db = DatabaseConnection("postgresql://user:pass@localhost/mydb")
        >>> 
        >>> # 执行查询
        >>> with db.connect() as conn:
        ...     result = db.execute_query("SELECT * FROM products LIMIT 10", conn)
        ...     print(result)  # DataFrame
    """
    
    def __init__(
        self,
        connection_string: str,
        pool_size: int = 5,
        max_overflow: int = 10,
        pool_timeout: int = 30,
        **engine_kwargs
    ):
        """初始化数据库连接
        
        Args:
            connection_string: 数据库连接字符串
            pool_size: 连接池大小
            max_overflow: 最大溢出连接数
            pool_timeout: 连接超时时间（秒）
            **engine_kwargs: 传递给 SQLAlchemy create_engine 的其他参数
        
        Raises:
            ValueError: 连接字符串无效
            ImportError: 缺少必要的数据库驱动
        """
        self.connection_string = connection_string
        
        # 解析连接字符串获取数据库类型
        parsed = urlparse(connection_string)
        self.dialect = parsed.scheme.split('+')[0]  # e.g., "mysql+pymysql" -> "mysql"
        
        # 创建引擎
        try:
            self.engine = sa.create_engine(
                connection_string,
                pool_size=pool_size,
                max_overflow=max_overflow,
                pool_timeout=pool_timeout,
                **engine_kwargs
            )
        except Exception as e:
            raise ValueError(f"Failed to create database engine: {e}")
    
    @contextmanager
    def connect(self):
        """获取数据库连接（上下文管理器）
        
        Yields:
            SQLAlchemy Connection 对象
        
        Examples:
            >>> with db.connect() as conn:
            ...     result = conn.execute(text("SELECT 1"))
        """
        conn = self.engine.connect()
        try:
            yield conn
        finally:
            conn.close()
    
    def get_inspector(self):
        """获取 SQLAlchemy Inspector
        
        Returns:
            SQLAlchemy Inspector 对象，用于数据库内省
        
        Examples:
            >>> inspector = db.get_inspector()
            >>> tables = inspector.get_table_names()
            >>> columns = inspector.get_columns('users')
        """
        return inspect(self.engine)
    
    def execute_query(
        self,
        sql: str,
        conn: Optional[Connection] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> pd.DataFrame:
        """执行 SQL 查询并返回 DataFrame
        
        Args:
            sql: SQL 查询语句
            conn: 数据库连接（可选，如果不提供则创建临时连接）
            params: SQL 参数（用于防止 SQL 注入）
        
        Returns:
            查询结果 DataFrame
        
        Raises:
            Exception: SQL 执行错误
        
        Examples:
            >>> # 方式 1: 使用临时连接
            >>> df = db.execute_query("SELECT * FROM users WHERE age > :age", params={"age": 18})
            >>> 
            >>> # 方式 2: 使用现有连接
            >>> with db.connect() as conn:
            ...     df1 = db.execute_query("SELECT * FROM users", conn=conn)
            ...     df2 = db.execute_query("SELECT * FROM products", conn=conn)
        """
        if conn is not None:
            # 使用提供的连接
            return pd.read_sql(text(sql), conn, params=params)
        else:
            # 创建临时连接
            with self.connect() as conn:
                return pd.read_sql(text(sql), conn, params=params)
    
    def get_table_names(self) -> List[str]:
        """获取所有表名
        
        Returns:
            表名列表
        
        Examples:
            >>> tables = db.get_table_names()
            >>> print(tables)  # ['users', 'products', 'orders']
        """
        inspector = self.get_inspector()
        return inspector.get_table_names()
    
    def get_schema_info(self, tables: Optional[List[str]] = None) -> Dict[str, Any]:
        """获取数据库 schema 信息
        
        Args:
            tables: 要获取信息的表名列表，None 表示所有表
        
        Returns:
            Schema 信息字典，包含：
            - tables: 表名列表
            - columns: 每个表的列信息
            - foreign_keys: 外键关系
            - indexes: 索引信息
            - primary_keys: 主键信息
        
        Examples:
            >>> schema = db.get_schema_info()
            >>> print(schema["tables"])  # ['users', 'products']
            >>> print(schema["columns"]["users"])  # [{'name': 'id', 'type': 'INTEGER', ...}]
        """
        inspector = self.get_inspector()
        
        # 获取表名
        if tables is None:
            tables = inspector.get_table_names()
        
        schema_info = {
            "tables": tables,
            "columns": {},
            "foreign_keys": {},
            "indexes": {},
            "primary_keys": {},
        }
        
        for table in tables:
            # 列信息
            columns = inspector.get_columns(table)
            schema_info["columns"][table] = [
                {
                    "name": col["name"],
                    "type": str(col["type"]),
                    "nullable": col.get("nullable", True),
                    "default": col.get("default"),
                    "autoincrement": col.get("autoincrement", False),
                }
                for col in columns
            ]
            
            # 主键
            pk = inspector.get_pk_constraint(table)
            schema_info["primary_keys"][table] = pk.get("constrained_columns", [])
            
            # 外键
            foreign_keys = inspector.get_foreign_keys(table)
            schema_info["foreign_keys"][table] = [
                {
                    "constrained_columns": fk["constrained_columns"],
                    "referred_table": fk["referred_table"],
                    "referred_columns": fk["referred_columns"],
                }
                for fk in foreign_keys
            ]
            
            # 索引
            indexes = inspector.get_indexes(table)
            schema_info["indexes"][table] = [
                {
                    "name": idx["name"],
                    "columns": idx["column_names"],
                    "unique": idx.get("unique", False),
                }
                for idx in indexes
            ]
        
        return schema_info
    
    def get_sample_data(
        self,
        tables: Optional[List[str]] = None,
        sample_size: int = 5,
        max_value_length: int = 100
    ) -> Dict[str, Dict[str, List[Any]]]:
        """获取表的示例数据
        
        获取非重复、非 NULL、按长度从小到大排序的前几个示例值。
        对于字符串值，会过滤掉超过最大长度的值以避免 Prompt 过大。
        
        Args:
            tables: 要获取示例的表名列表，None 表示所有表
            sample_size: 每个列的示例值数量
            max_value_length: 字符串值的最大长度限制
        
        Returns:
            示例数据字典: {table_name: {column_name: [value1, value2, ...]}}
        
        Examples:
            >>> samples = db.get_sample_data(tables=["users"], sample_size=3)
            >>> print(samples["users"]["name"])  # ["Alice", "Bob", "Charlie"]
        """
        if tables is None:
            tables = self.get_table_names()
        
        samples = {}
        
        with self.connect() as conn:
            for table in tables:
                try:
                    # 获取列信息
                    inspector = self.get_inspector()
                    columns = inspector.get_columns(table)
                    
                    table_samples = {}
                    
                    for col_info in columns:
                        col_name = col_info["name"]
                        col_type = str(col_info["type"])
                        
                        # 对于字符串类型列，按长度排序并过滤长度
                        if any(t in col_type.upper() for t in ["CHAR", "TEXT", "STRING", "VARCHAR"]):
                            # 获取非 NULL、非重复的值，按长度排序
                            if self.dialect == "sqlite":
                                length_func = "LENGTH"
                            elif self.dialect == "mysql":
                                length_func = "CHAR_LENGTH"
                            else:  # PostgreSQL
                                length_func = "LENGTH"
                            
                            sql = f"""
                                SELECT DISTINCT {col_name}
                                FROM {table}
                                WHERE {col_name} IS NOT NULL 
                                  AND {length_func}({col_name}) <= {max_value_length}
                                ORDER BY {length_func}({col_name}) ASC
                                LIMIT {sample_size}
                            """
                        else:
                            # 对于非字符串列，直接获取非 NULL、非重复的值
                            sql = f"""
                                SELECT DISTINCT {col_name}
                                FROM {table}
                                WHERE {col_name} IS NOT NULL
                                ORDER BY {col_name} ASC
                                LIMIT {sample_size}
                            """
                        
                        try:
                            result = pd.read_sql(text(sql), conn)
                            values = result[col_name].tolist()
                            
                            # 对字符串值再次检查长度（防止不同数据库的差异）
                            if values and isinstance(values[0], str):
                                values = [v for v in values if len(str(v)) <= max_value_length]
                            
                            table_samples[col_name] = values
                        except Exception as e:
                            # 如果某列查询失败，记录空列表
                            table_samples[col_name] = []
                    
                    samples[table] = table_samples
                    
                except Exception as e:
                    # 如果某个表查询失败，记录错误但继续处理其他表
                    samples[table] = {"error": str(e)}
        
        return samples
    
    def get_table_statistics(
        self,
        tables: Optional[List[str]] = None
    ) -> Dict[str, Dict[str, Any]]:
        """获取表的统计信息
        
        Args:
            tables: 要统计的表名列表，None 表示所有表
        
        Returns:
            统计信息字典: {
                table_name: {
                    "row_count": int,
                    "columns": {
                        column_name: {
                            "unique_count": int,
                            "null_count": int,
                            "min": value (numeric only),
                            "max": value (numeric only),
                        }
                    }
                }
            }
        
        Examples:
            >>> stats = db.get_table_statistics(tables=["users"])
            >>> print(stats["users"]["row_count"])  # 1000
            >>> print(stats["users"]["columns"]["age"]["unique_count"])  # 50
        """
        if tables is None:
            tables = self.get_table_names()
        
        statistics = {}
        
        with self.connect() as conn:
            for table in tables:
                try:
                    # 行数
                    count_sql = f"SELECT COUNT(*) as cnt FROM {table}"
                    row_count = pd.read_sql(text(count_sql), conn)["cnt"][0]
                    
                    # 获取列信息
                    inspector = self.get_inspector()
                    columns = inspector.get_columns(table)
                    
                    column_stats = {}
                    for col_info in columns:
                        col_name = col_info["name"]
                        col_type = str(col_info["type"])
                        
                        # 唯一值和空值统计
                        unique_sql = f"SELECT COUNT(DISTINCT {col_name}) as unique_cnt FROM {table}"
                        null_sql = f"SELECT COUNT(*) as null_cnt FROM {table} WHERE {col_name} IS NULL"
                        
                        unique_count = pd.read_sql(text(unique_sql), conn)["unique_cnt"][0]
                        null_count = pd.read_sql(text(null_sql), conn)["null_cnt"][0]
                        
                        col_stat = {
                            "type": col_type,
                            "unique_count": int(unique_count),
                            "null_count": int(null_count),
                        }
                        
                        # 数值列的 min/max
                        if "INT" in col_type.upper() or "FLOAT" in col_type.upper() or "DECIMAL" in col_type.upper() or "NUMERIC" in col_type.upper():
                            try:
                                minmax_sql = f"SELECT MIN({col_name}) as min_val, MAX({col_name}) as max_val FROM {table}"
                                minmax_result = pd.read_sql(text(minmax_sql), conn)
                                col_stat["min"] = minmax_result["min_val"][0]
                                col_stat["max"] = minmax_result["max_val"][0]
                            except:
                                pass  # 如果计算失败，跳过
                        
                        column_stats[col_name] = col_stat
                    
                    statistics[table] = {
                        "row_count": int(row_count),
                        "columns": column_stats,
                    }
                    
                except Exception as e:
                    statistics[table] = {"error": str(e)}
        
        return statistics
    
    def test_connection(self) -> bool:
        """测试数据库连接是否正常
        
        Returns:
            True 如果连接成功，False 否则
        
        Examples:
            >>> if db.test_connection():
            ...     print("Connection OK")
        """
        try:
            with self.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception:
            return False
    
    def close(self):
        """关闭连接池
        
        Examples:
            >>> db.close()
        """
        if self.engine:
            self.engine.dispose()



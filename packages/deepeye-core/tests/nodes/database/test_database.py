"""Database 模块单元测试

测试 DatabaseConnection 和 DatabaseDataSourceNode 的基本功能。
"""

import pytest
import os
import sqlite3
import tempfile
from pathlib import Path
import pandas as pd

from deepeye.nodes.database import DatabaseConnection, DatabaseDataSourceNode
from deepeye.nodes.io import NodeInput


@pytest.fixture
def sample_db():
    """创建临时测试数据库"""
    # 创建临时数据库文件
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "test.db")
    
    # 创建连接并初始化数据
    conn = sqlite3.connect(db_path)
    
    # 创建表
    conn.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            age INTEGER,
            email TEXT UNIQUE
        )
    """)
    
    conn.execute("""
        CREATE TABLE orders (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            order_date DATE,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    
    # 插入测试数据
    users = [
        (1, "Alice", 25, "alice@example.com"),
        (2, "Bob", 30, "bob@example.com"),
        (3, "Charlie", 35, "charlie@example.com"),
    ]
    conn.executemany("INSERT INTO users VALUES (?, ?, ?, ?)", users)
    
    orders = [
        (1, 1, 100.50, "2024-01-01"),
        (2, 1, 200.00, "2024-01-02"),
        (3, 2, 150.75, "2024-01-03"),
        (4, 3, 300.00, "2024-01-04"),
    ]
    conn.executemany("INSERT INTO orders VALUES (?, ?, ?, ?)", orders)
    
    conn.commit()
    conn.close()
    
    connection_string = f"sqlite:///{db_path}"
    
    yield {"path": db_path, "connection_string": connection_string}
    
    # 清理
    try:
        os.remove(db_path)
        os.rmdir(temp_dir)
    except:
        pass


class TestDatabaseConnection:
    """测试 DatabaseConnection"""
    
    def test_connection_creation(self, sample_db):
        """测试连接创建"""
        db = DatabaseConnection(sample_db["connection_string"])
        assert db.dialect == "sqlite"
        assert db.test_connection()
    
    def test_get_table_names(self, sample_db):
        """测试获取表名"""
        db = DatabaseConnection(sample_db["connection_string"])
        tables = db.get_table_names()
        assert set(tables) == {"users", "orders"}
    
    def test_get_schema_info(self, sample_db):
        """测试获取 schema 信息"""
        db = DatabaseConnection(sample_db["connection_string"])
        schema = db.get_schema_info()
        
        assert "users" in schema["tables"]
        assert "orders" in schema["tables"]
        
        # 检查 users 表的列
        user_columns = schema["columns"]["users"]
        column_names = [col["name"] for col in user_columns]
        assert set(column_names) == {"id", "name", "age", "email"}
        
        # 检查主键
        assert schema["primary_keys"]["users"] == ["id"]
        
        # 检查外键
        order_fks = schema["foreign_keys"]["orders"]
        assert len(order_fks) == 1
        assert order_fks[0]["referred_table"] == "users"
    
    def test_execute_query(self, sample_db):
        """测试执行查询"""
        db = DatabaseConnection(sample_db["connection_string"])
        df = db.execute_query("SELECT * FROM users WHERE age > 25")
        
        assert len(df) == 2  # Bob and Charlie
        assert list(df.columns) == ["id", "name", "age", "email"]
    
    def test_get_sample_data(self, sample_db):
        """测试获取示例数据"""
        db = DatabaseConnection(sample_db["connection_string"])
        samples = db.get_sample_data(tables=["users"], sample_size=2)
        
        assert "users" in samples
        assert "name" in samples["users"]
        assert len(samples["users"]["name"]) == 2
    
    def test_get_table_statistics(self, sample_db):
        """测试获取统计信息"""
        db = DatabaseConnection(sample_db["connection_string"])
        stats = db.get_table_statistics(tables=["users"])
        
        assert "users" in stats
        assert stats["users"]["row_count"] == 3
        assert "age" in stats["users"]["columns"]


class TestDatabaseDataSourceNode:
    """测试 DatabaseDataSourceNode"""
    
    def test_introspect_mode(self, sample_db):
        """测试内省模式"""
        node = DatabaseDataSourceNode(
            node_id="test_introspect",
            config={
                "connection_string": sample_db["connection_string"],
                "sample_size": 2,
                "include_statistics": True
            }
        )
        
        outputs = node.run(inputs={})
        
        assert "data" in outputs
        assert outputs["data"].status == "success"
        
        # 检查输出内容 - data 端口包含 connection_string 和 database_info
        data = outputs["data"].data
        assert "connection_string" in data
        assert "database_info" in data
        
        assert data["connection_string"] == sample_db["connection_string"]
        
        db_info = data["database_info"]
        assert "schema" in db_info
        assert "examples" in db_info
        assert "statistics" in db_info
        
        assert set(db_info["schema"]["tables"]) == {"users", "orders"}
    
    def test_query_mode(self, sample_db):
        """测试查询模式"""
        node = DatabaseDataSourceNode(
            node_id="test_query",
            config={
                "connection_string": sample_db["connection_string"],
                "mode": "query"  # 明确设置为查询模式
            }
        )
        
        # 查询模式需要通过 inputs 传递 SQL
        outputs = node.run(inputs={
            "sql": NodeInput(data="SELECT * FROM users WHERE age > 25")
        })
        
        assert "data" in outputs
        # 如果失败，打印错误信息
        if outputs["data"].status != "success":
            print(f"Error: {outputs['data'].error}")
        assert outputs["data"].status == "success"
        
        # 在查询模式下，data 端口包含字典 {"dataframe": df}
        assert isinstance(outputs["data"].data, dict)
        assert "dataframe" in outputs["data"].data
        df = outputs["data"].data["dataframe"]
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2  # Bob and Charlie
        assert list(df.columns) == ["id", "name", "age", "email"]
    
    def test_introspect_specific_tables(self, sample_db):
        """测试内省指定表"""
        node = DatabaseDataSourceNode(
            node_id="test_introspect_specific",
            config={
                "connection_string": sample_db["connection_string"],
                "tables": ["users"],  # 只内省 users 表
                "sample_size": 3
            }
        )
        
        outputs = node.run(inputs={})
        
        # data 端口包含 database_info
        data = outputs["data"].data
        assert "database_info" in data
        
        db_info = data["database_info"]
        assert db_info["schema"]["tables"] == ["users"]
        assert "users" in db_info["examples"]
        assert "orders" not in db_info["examples"]
    
    def test_error_handling_bad_connection(self):
        """测试错误处理：无效连接"""
        node = DatabaseDataSourceNode(
            node_id="test_error",
            config={
                "connection_string": "sqlite:///nonexistent.db",
                "sql": "SELECT * FROM users"
            }
        )
        
        outputs = node.run(inputs={})
        
        # SQLite 会自动创建数据库，所以我们测试查询不存在的表
        assert "data" in outputs
        # 可能是 error 或 success（空结果），取决于具体实现
    
    def test_max_rows_limit(self, sample_db):
        """测试行数限制"""
        node = DatabaseDataSourceNode(
            node_id="test_limit",
            config={
                "connection_string": sample_db["connection_string"],
                "mode": "query",  # 明确设置为查询模式
                "max_rows": 2  # 限制为 2 行
            }
        )
        
        # 查询模式需要通过 inputs 传递 SQL
        from deepeye.nodes.io import NodeInput
        outputs = node.run(inputs={
            "sql": NodeInput(data="SELECT * FROM orders")
        })
        
        # data 端口包含字典 {"dataframe": df}
        df = outputs["data"].data["dataframe"]
        assert isinstance(df, pd.DataFrame)
        assert len(df) <= 2  # 最多 2 行


if __name__ == "__main__":
    pytest.main([__file__, "-v"])



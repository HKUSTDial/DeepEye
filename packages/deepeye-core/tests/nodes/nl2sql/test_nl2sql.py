"""NL2SQL 模块单元测试

测试 NL2SQLNode 的基本功能（使用 mock LLM）。
"""

import pytest
import os
import sqlite3
import tempfile
from unittest.mock import Mock, patch

from deepeye.nodes.nl2sql import NL2SQLNode
from deepeye.nodes.nl2sql.prompt import (
    format_schema_info,
    format_sample_data,
    format_statistics_info,
    extract_response_parts,
)
from deepeye.nodes.io import NodeInput


@pytest.fixture
def sample_db():
    """创建临时测试数据库"""
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "test.db")
    
    conn = sqlite3.connect(db_path)
    
    conn.execute("""
        CREATE TABLE products (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            price REAL NOT NULL
        )
    """)
    
    products = [
        (1, "Laptop", 999.99),
        (2, "Mouse", 29.99),
        (3, "Keyboard", 79.99),
    ]
    conn.executemany("INSERT INTO products VALUES (?, ?, ?)", products)
    
    conn.commit()
    conn.close()
    
    connection_string = f"sqlite:///{db_path}"
    
    yield {"path": db_path, "connection_string": connection_string}
    
    try:
        os.remove(db_path)
        os.rmdir(temp_dir)
    except:
        pass


@pytest.fixture
def sample_database_info():
    """示例数据库信息"""
    return {
        "dialect": "sqlite",
        "schema": {
            "tables": ["products"],
            "columns": {
                "products": [
                    {"name": "id", "type": "INTEGER", "nullable": False, "autoincrement": True},
                    {"name": "name", "type": "TEXT", "nullable": False},
                    {"name": "price", "type": "REAL", "nullable": False},
                ]
            },
            "primary_keys": {"products": ["id"]},
            "foreign_keys": {"products": []},
            "indexes": {"products": []},
        },
        "examples": {
            "products": {
                "id": [1, 2, 3],
                "name": ["Laptop", "Mouse", "Keyboard"],
                "price": [999.99, 29.99, 79.99],
            }
        },
        "statistics": {
            "products": {
                "row_count": 3,
                "columns": {
                    "id": {"type": "INTEGER", "unique_count": 3, "null_count": 0},
                    "name": {"type": "TEXT", "unique_count": 3, "null_count": 0},
                    "price": {"type": "REAL", "unique_count": 3, "null_count": 0, "min": 29.99, "max": 999.99},
                }
            }
        }
    }


class TestPromptFormatting:
    """测试 Prompt 格式化功能"""
    
    def test_format_schema_info(self, sample_database_info):
        """测试 schema 格式化"""
        schema = sample_database_info["schema"]
        formatted = format_schema_info(schema)
        
        assert "products" in formatted
        assert "id" in formatted
        assert "name" in formatted
        assert "price" in formatted
        assert "INTEGER" in formatted
        assert "TEXT" in formatted
        assert "REAL" in formatted
    
    def test_format_sample_data(self, sample_database_info):
        """测试示例数据格式化"""
        examples = sample_database_info["examples"]
        formatted = format_sample_data(examples)
        
        assert "products" in formatted
        assert "Laptop" in formatted
        assert "999.99" in formatted
    
    def test_format_statistics_info(self, sample_database_info):
        """测试统计信息格式化"""
        statistics = sample_database_info["statistics"]
        formatted = format_statistics_info(statistics)
        
        assert "products" in formatted
        assert "3" in formatted  # row_count
        assert "unique values" in formatted
    
    def test_extract_response_parts_valid(self):
        """测试提取有效响应"""
        response = """
        <think>
        I need to select all products.
        </think>
        
        <sql>
        SELECT * FROM products ORDER BY price DESC
        </sql>
        
        <explanation>
        This query selects all products and orders them by price in descending order.
        </explanation>
        """
        
        parts = extract_response_parts(response)
        
        assert "think" in parts
        assert "sql" in parts
        assert "explanation" in parts
        assert "SELECT * FROM products" in parts["sql"]
    
    def test_extract_response_parts_missing_sql(self):
        """测试缺少 SQL 标签的响应"""
        response = """
        <think>
        Some thinking
        </think>
        
        <explanation>
        Some explanation
        </explanation>
        """
        
        with pytest.raises(ValueError, match="无法从 LLM 响应中提取 SQL 语句"):
            extract_response_parts(response)


class TestNL2SQLNode:
    """测试 NL2SQLNode"""
    
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    def test_node_initialization(self):
        """测试节点初始化"""
        node = NL2SQLNode(
            node_id="test_nl2sql",
            config={
                "api_key": "test-key",
                "model": "gpt-4",
                "max_retries": 2
            }
        )
        
        assert node.node_id == "test_nl2sql"
        assert node.config.model == "gpt-4"
        assert node.config.max_retries == 2
        assert len(node.input_ports) == 2  # database 和 query
        assert len(node.output_ports) == 1  # 只有 data 端口
    
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    @patch("deepeye.nodes.nl2sql.nl2sql.LLMClient")
    def test_successful_sql_generation(self, mock_llm_client, sample_db, sample_database_info):
        """测试成功的 SQL 生成和执行"""
        # Mock LLM 响应
        mock_client_instance = Mock()
        mock_client_instance.chat.return_value = """
        <think>
        Need to select all products ordered by price descending.
        </think>
        
        <sql>
        SELECT * FROM products ORDER BY price DESC
        </sql>
        
        <explanation>
        This query retrieves all products and sorts them by price in descending order.
        </explanation>
        """
        mock_llm_client.return_value = mock_client_instance
        
        # 创建节点
        node = NL2SQLNode(
            node_id="test_nl2sql",
            config={
                "api_key": "test-key",
                "model": "gpt-4",
                "verbose": False
            }
        )
        
        # 执行 - 现在输入格式是 database 端口包含 connection_string 和 database_info
        outputs = node.run({
            "database": NodeInput(data={
                "connection_string": sample_db["connection_string"],
                "database_info": sample_database_info
            }),
            "query": NodeInput(data="Show me all products sorted by price")
        })
        
        # 验证输出 - 现在只有一个 data 端口，包含 sql、dataframe 和 explanation
        assert outputs["data"].status == "success"
        
        result = outputs["data"].data
        assert "SELECT * FROM products" in result["sql"]
        assert len(result["dataframe"]) == 3  # 3 products
        assert outputs["data"].metadata["retries"] == 0
    
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    @patch("deepeye.nodes.nl2sql.nl2sql.LLMClient")
    def test_sql_error_and_retry(self, mock_llm_client, sample_db, sample_database_info):
        """测试 SQL 错误和自动修复"""
        mock_client_instance = Mock()
        
        # 第一次返回错误的 SQL
        # 第二次返回正确的 SQL
        mock_client_instance.chat.side_effect = [
            """
            <think>First attempt</think>
            <sql>SELECT * FROM nonexistent_table</sql>
            <explanation>This will fail</explanation>
            """,
            """
            <think>Fixing the error</think>
            <sql>SELECT * FROM products</sql>
            <explanation>Corrected query</explanation>
            """
        ]
        mock_llm_client.return_value = mock_client_instance
        
        node = NL2SQLNode(
            node_id="test_nl2sql",
            config={
                "api_key": "test-key",
                "model": "gpt-4",
                "max_retries": 2,
                "verbose": False
            }
        )
        
        outputs = node.run({
            "database": NodeInput(data={
                "connection_string": sample_db["connection_string"],
                "database_info": sample_database_info
            }),
            "query": NodeInput(data="Show me all products")
        })
        
        # 应该成功（经过1次重试）
        assert outputs["data"].status == "success"
        assert outputs["data"].metadata["retries"] == 1
        result = outputs["data"].data
        assert len(result["dataframe"]) == 3
    
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    @patch("deepeye.nodes.nl2sql.nl2sql.LLMClient")
    def test_max_retries_exceeded(self, mock_llm_client, sample_db, sample_database_info):
        """测试超过最大重试次数"""
        mock_client_instance = Mock()
        
        # 所有尝试都返回错误的 SQL
        mock_client_instance.chat.return_value = """
        <think>Bad SQL</think>
        <sql>SELECT * FROM nonexistent_table</sql>
        <explanation>This will always fail</explanation>
        """
        mock_llm_client.return_value = mock_client_instance
        
        node = NL2SQLNode(
            node_id="test_nl2sql",
            config={
                "api_key": "test-key",
                "model": "gpt-4",
                "max_retries": 2,
                "verbose": False
            }
        )
        
        outputs = node.run({
            "database": NodeInput(data={
                "connection_string": sample_db["connection_string"],
                "database_info": sample_database_info
            }),
            "query": NodeInput(data="Show me all products")
        })
        
        # 应该失败
        assert outputs["data"].status == "failed"
        assert outputs["data"].metadata["retries"] == 3  # 初始 + 2次重试
        assert "error" in outputs["data"].metadata
    
    @patch.dict(os.environ, {"OPENAI_API_KEY": ""}, clear=True)
    def test_missing_api_key(self):
        """测试缺少 API Key"""
        with pytest.raises(ValueError, match="需要 API Key"):
            NL2SQLNode(
                node_id="test_nl2sql",
                config={
                    "model": "gpt-4"
                }
            )
    
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    def test_missing_inputs(self):
        """测试缺少必要输入"""
        node = NL2SQLNode(
            node_id="test_nl2sql",
            config={
                "api_key": "test-key",
                "model": "gpt-4"
            }
        )
        
        # 缺少 query 输入
        outputs = node.run({
            "database": NodeInput(data={
                "connection_string": "sqlite:///test.db",
                "database_info": {}
            })
        })
        
        assert outputs["data"].status == "failed"
        # 错误信息在 error 字段而不是 metadata 中
        assert "缺少必需的输入端口" in (outputs["data"].error or "")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])



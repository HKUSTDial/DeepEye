"""Pytest 配置文件"""

import pytest
from typing import Generator


@pytest.fixture
def sample_workflow_config() -> dict:
    """示例工作流配置"""
    return {
        "name": "测试工作流",
        "description": "用于测试的简单工作流",
        "nodes": {
            "node1": {
                "type": "DataSource",
                "config": {"source": "test.db"}
            },
            "node2": {
                "type": "NL2SQL",
                "config": {}
            }
        },
        "edges": [
            {"from": "node1", "to": "node2"}
        ]
    }


@pytest.fixture
def sample_node_input() -> dict:
    """示例节点输入"""
    return {
        "query": "查询所有用户",
        "context": {}
    }


@pytest.fixture
def mock_llm_response() -> str:
    """模拟 LLM 响应"""
    return "SELECT * FROM users;"


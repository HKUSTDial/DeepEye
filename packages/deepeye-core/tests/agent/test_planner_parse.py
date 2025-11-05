"""测试 PlannerAgent 的 JSON 解析功能"""

import pytest
from deepeye.agent.planner import PlannerAgent
from deepeye.llm.client import LLMClient


class TestPlannerParse:
    """测试 PlannerAgent 的响应解析功能"""
    
    @pytest.fixture
    def planner(self):
        """创建一个 PlannerAgent 实例（无需真实 LLM）"""
        # 创建一个 mock LLM client (不会真正调用)
        class MockLLMClient:
            pass
        
        return PlannerAgent(MockLLMClient())
    
    def test_parse_pure_json(self, planner):
        """测试解析纯 JSON"""
        content = """{
            "steps": [
                {
                    "step_id": 1,
                    "tool": "NL2SQL",
                    "description": "转换查询"
                }
            ]
        }"""
        
        result = planner._parse_plan_response(content)
        assert "steps" in result
        assert len(result["steps"]) == 1
        assert result["steps"][0]["tool"] == "NL2SQL"
    
    def test_parse_json_in_code_block(self, planner):
        """测试解析 markdown 代码块中的 JSON"""
        content = """这是执行计划：
        
```json
{
    "steps": [
        {
            "step_id": 1,
            "tool": "DataCoder",
            "description": "处理数据"
        }
    ]
}
```
"""
        
        result = planner._parse_plan_response(content)
        assert "steps" in result
        assert result["steps"][0]["tool"] == "DataCoder"
    
    def test_parse_json_in_code_block_no_lang(self, planner):
        """测试解析没有语言标记的代码块"""
        content = """```
{
    "steps": [
        {
            "step_id": 1,
            "tool": "DataPlot"
        }
    ]
}
```"""
        
        result = planner._parse_plan_response(content)
        assert "steps" in result
        assert result["steps"][0]["tool"] == "DataPlot"
    
    def test_parse_json_with_text_before_and_after(self, planner):
        """测试提取包含在其他文本中的 JSON"""
        content = """下面是我生成的执行计划：

{
    "steps": [
        {
            "step_id": 1,
            "tool": "NL2SQL",
            "description": "将自然语言转换为SQL"
        }
    ]
}

希望这个计划能满足您的需求。"""
        
        result = planner._parse_plan_response(content)
        assert "steps" in result
        assert result["steps"][0]["tool"] == "NL2SQL"
    
    def test_parse_nested_json(self, planner):
        """测试解析嵌套的 JSON"""
        content = """{
    "steps": [
        {
            "step_id": 1,
            "tool": "NL2SQL",
            "inputs": {
                "query": {
                    "value": "查询数据"
                }
            },
            "config": {
                "database": "test_db"
            }
        }
    ]
}"""
        
        result = planner._parse_plan_response(content)
        assert "steps" in result
        assert result["steps"][0]["inputs"]["query"]["value"] == "查询数据"
        assert result["steps"][0]["config"]["database"] == "test_db"
    
    def test_parse_multiple_json_objects(self, planner):
        """测试当有多个 JSON 对象时，选择包含 steps 的那个"""
        content = """
先看看这个示例：{"example": "data"}

然后是真正的计划：
{
    "steps": [
        {
            "step_id": 1,
            "tool": "DataCoder"
        }
    ]
}
"""
        
        result = planner._parse_plan_response(content)
        assert "steps" in result
        assert result["steps"][0]["tool"] == "DataCoder"
    
    def test_parse_invalid_json_raises_error(self, planner):
        """测试无效 JSON 抛出错误"""
        content = "这不是有效的 JSON"
        
        with pytest.raises(ValueError, match="无法从响应中提取有效的 JSON"):
            planner._parse_plan_response(content)
    
    def test_parse_json_without_steps_still_parses(self, planner):
        """测试没有 steps 字段的 JSON 仍会被解析（方法3会解析任何有效JSON）"""
        content = """{"other_field": "value"}"""
        
        # 这不会抛出错误，但会返回一个没有 steps 的字典
        result = planner._parse_plan_response(content)
        assert "other_field" in result
        assert "steps" not in result
    
    def test_parse_json_with_unicode(self, planner):
        """测试包含中文等 Unicode 字符的 JSON"""
        content = """{
    "steps": [
        {
            "step_id": 1,
            "tool": "NL2SQL",
            "description": "将自然语言查询转换为SQL语句"
        }
    ]
}"""
        
        result = planner._parse_plan_response(content)
        assert "步骤" not in result["steps"][0]["description"]  # 验证解析正确
        assert "自然语言" in result["steps"][0]["description"]


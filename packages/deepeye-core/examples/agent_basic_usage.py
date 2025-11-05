"""Agent 基础使用示例

演示如何使用 PlannerAgent 来规划和执行任务。

注意：需要设置环境变量 OPENAI_API_KEY 或在代码中提供 API key。
"""

import os
from deepeye.llm import LLMClient
from deepeye.agent import PlannerAgent
from deepeye.nodes.base import BaseNode, NodeMetadata
from deepeye.nodes.io import NodeInput, NodeOutput, NodeInputPort, NodeOutputPort


# 定义一些简单的示例节点

class DataQueryNode(BaseNode):
    """数据查询节点（模拟）"""
    
    node_type = "DataQuery"
    
    def __init__(self, node_id=None, config=None):
        super().__init__(node_id, config)
        
        self.metadata = NodeMetadata(
            name="DataQuery",
            display_name="数据查询",
            description="从数据库查询数据",
            category="data_processing",
            semantic_description="连接数据库并执行 SQL 查询，返回查询结果",
            capabilities=["database", "query", "sql"],
            use_cases=[
                "查询销售数据",
                "获取用户信息",
                "统计分析数据"
            ],
            input_description={"query": "SQL 查询语句"},
            output_description={"data": "查询结果数据"},
        )
        
        self.input_ports = [
            NodeInputPort(name="query", label="查询语句", required=True)
        ]
        
        self.output_ports = [
            NodeOutputPort(name="data", label="数据")
        ]
    
    def execute(self, inputs):
        # 模拟查询
        query = inputs.get("query", NodeInput(data="SELECT * FROM sales")).data
        
        # 返回模拟数据
        mock_data = [
            {"date": "2024-01", "sales": 1000},
            {"date": "2024-02", "sales": 1200},
            {"date": "2024-03", "sales": 1500},
        ]
        
        return {"data": NodeOutput(data=mock_data)}


class DataAnalysisNode(BaseNode):
    """数据分析节点（模拟）"""
    
    node_type = "DataAnalysis"
    
    def __init__(self, node_id=None, config=None):
        super().__init__(node_id, config)
        
        self.metadata = NodeMetadata(
            name="DataAnalysis",
            display_name="数据分析",
            description="对数据进行统计分析",
            category="data_processing",
            semantic_description="对输入数据进行统计分析，计算均值、总和、趋势等",
            capabilities=["analysis", "statistics", "aggregation"],
            use_cases=[
                "计算销售总额",
                "分析数据趋势",
                "统计汇总"
            ],
            input_description={"data": "待分析的数据"},
            output_description={"result": "分析结果"},
        )
        
        self.input_ports = [
            NodeInputPort(name="data", label="数据", required=True)
        ]
        
        self.output_ports = [
            NodeOutputPort(name="result", label="分析结果")
        ]
    
    def execute(self, inputs):
        data = inputs.get("data", NodeInput(data=[])).data
        
        # 简单分析
        if isinstance(data, list) and data:
            total = sum(item.get("sales", 0) for item in data if isinstance(item, dict))
            avg = total / len(data) if data else 0
            
            result = {
                "total": total,
                "average": avg,
                "count": len(data),
            }
        else:
            result = {"error": "Invalid data"}
        
        return {"result": NodeOutput(data=result)}


class DataVisualizationNode(BaseNode):
    """数据可视化节点（模拟）"""
    
    node_type = "DataVisualization"
    
    def __init__(self, node_id=None, config=None):
        super().__init__(node_id, config)
        
        self.metadata = NodeMetadata(
            name="DataVisualization",
            display_name="数据可视化",
            description="生成数据图表",
            category="visualization",
            semantic_description="将数据转换为可视化图表，支持折线图、柱状图、饼图等",
            capabilities=["visualization", "chart", "plot"],
            use_cases=[
                "生成销售趋势图",
                "绘制数据分布图",
                "创建仪表板"
            ],
            input_description={"data": "要可视化的数据"},
            output_description={"chart": "生成的图表"},
        )
        
        self.input_ports = [
            NodeInputPort(name="data", label="数据", required=True)
        ]
        
        self.output_ports = [
            NodeOutputPort(name="chart", label="图表")
        ]
    
    def execute(self, inputs):
        data = inputs.get("data", NodeInput(data=None)).data
        
        # 模拟生成图表
        chart_info = {
            "type": "line_chart",
            "data_points": len(data) if isinstance(data, list) else 0,
            "status": "generated",
        }
        
        return {"chart": NodeOutput(data=chart_info)}


def main():
    """主函数"""
    
    print("=== Agent 基础使用示例 ===\n")
    
    # 1. 初始化 LLM 客户端
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("错误: 请设置环境变量 OPENAI_API_KEY")
        print("或修改代码直接提供 API key")
        return
    
    print("1. 初始化 LLM 客户端...")
    llm_client = LLMClient(
        api_key=api_key,
        base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
    )
    
    # 2. 创建 Planner Agent
    print("2. 创建 Planner Agent...")
    agent = PlannerAgent(
        llm_client=llm_client,
        model="gpt-3.5-turbo",
        temperature=0.3,
    )
    
    # 3. 注册可用节点
    print("3. 注册可用节点...")
    agent.register_node(DataQueryNode)
    agent.register_node(DataAnalysisNode)
    agent.register_node(DataVisualizationNode)
    
    print(f"   已注册 {len(agent.tool_registry)} 个工具\n")
    
    # 4. 执行任务（只生成计划，不执行）
    task = "查询销售数据，进行统计分析，然后生成可视化图表"
    print(f"4. 任务: {task}\n")
    print("5. 生成执行计划...")
    
    result = agent.run(task, auto_execute=False)
    
    # 6. 查看结果
    print("\n6. 执行结果:")
    print(f"   状态: {result.status.value}")
    print(f"   成功: {result.success}")
    
    if result.success:
        print("\n   执行计划:")
        for step in result.plan["steps"]:
            deps = f" (依赖: {step['depends_on']})" if step['depends_on'] else ""
            print(f"   步骤 {step['step_id']}: {step['tool']} - {step['description']}{deps}")
        
        print(f"\n   工作流信息:")
        print(f"   - 节点数: {len(result.workflow.list_nodes())}")
        print(f"   - 连接数: {len(result.workflow.get_connections())}")
        print(f"   - 节点列表: {', '.join(result.workflow.list_nodes())}")
    else:
        print(f"\n   错误: {result.error}")
    
    print("\n7. 日志:")
    for log in result.logs:
        print(f"   {log}")


if __name__ == "__main__":
    main()


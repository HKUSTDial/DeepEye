"""Planner Agent 快速开始示例

最简单的 PlannerAgent 使用示例。

使用方法：
    export DEEPEYE_LLM_API_KEY="sk-..."
    python examples/quickstart.py
"""

import os
from deepeye.llm import LLMClient
from deepeye.agent import PlannerAgent

# 导入节点
from deepeye.nodes.datasource import CSVDataSourceNode
from deepeye.nodes.datacoder import DataCoderNode
from deepeye.nodes.dataplot import DataPlotNode


def main():
    """快速开始示例"""
    
    # 1. 检查环境变量
    api_key = os.getenv("DEEPEYE_LLM_API_KEY")
    if not api_key:
        print("❌ 错误: 未设置环境变量 DEEPEYE_LLM_API_KEY")
        print("\n请先设置环境变量:")
        print("  export DEEPEYE_LLM_API_KEY='your-api-key'")
        print("  export DEEPEYE_LLM_BASE_URL='https://api.openai.com/v1'  # 可选")
        print("  export DEEPEYE_LLM_MODEL='gpt-4'  # 可选")
        return 1
    
    base_url = os.getenv("DEEPEYE_LLM_BASE_URL", "https://api.openai.com/v1")
    model = os.getenv("DEEPEYE_LLM_MODEL", "gpt-3.5-turbo")
    
    print("🤖 DeepEye Planner Agent - 快速开始")
    print("=" * 60)
    print(f"Base URL: {base_url}")
    print(f"Model: {model}")
    print()
    
    # 2. 创建 LLM 客户端
    llm_client = LLMClient(
        api_key=api_key,
        base_url=base_url,
        timeout=60,
    )
    
    # 3. 创建 Planner Agent
    agent = PlannerAgent(
        llm_client=llm_client,
        model=model,
        temperature=0.3,
    )
    
    # 4. 注册节点
    print("🔧 注册节点...")
    agent.register_node(CSVDataSourceNode)
    agent.register_node(DataCoderNode)
    agent.register_node(DataPlotNode)
    
    tools = agent.tool_registry.get_tool_names()
    print(f"✓ 已注册 {len(tools)} 个节点: {', '.join(tools)}")
    print()
    
    # 5. 定义任务
    task = "从sales.csv文件加载销售数据，筛选出销售额大于1000的记录，然后生成销售额的柱状图"
    
    print(f"📝 任务: {task}")
    print()
    
    # 6. 运行 Agent（不自动执行）
    print("🚀 开始规划...")
    result = agent.run(task, auto_execute=False)
    
    # 7. 输出结果
    print()
    print("=" * 60)
    print("📊 结果")
    print("=" * 60)
    print(f"状态: {result.status.value}")
    print(f"成功: {'✓' if result.success else '✗'}")
    print()
    
    if result.success:
        # 输出执行计划
        if result.plan:
            print("📋 执行计划:")
            for step in result.plan.get("steps", []):
                print(f"  步骤 {step['step_id']}: {step['description']}")
                print(f"    └─ 工具: {step['tool']}")
        
        print()
        
        # 输出工作流信息
        if result.workflow:
            print("🔄 工作流:")
            nodes = result.workflow.list_nodes()
            connections = result.workflow.get_connections()
            print(f"  节点数: {len(nodes)}")
            print(f"  连接数: {len(connections)}")
            print(f"  节点: {nodes}")
            
            if connections:
                print(f"  连接:")
                for conn in connections:
                    print(f"    {conn}")
        
        print()
        print("✓ 工作流生成成功! 可以使用 workflow.to_json() 导出")
        
    else:
        print(f"❌ 失败: {result.error}")
        print()
        print("📜 日志:")
        for log in result.logs:
            print(f"  {log}")
    
    print()
    print("=" * 60)
    
    return 0 if result.success else 1


if __name__ == "__main__":
    exit(main())


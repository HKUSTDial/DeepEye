"""Agent + GlobalConfig 集成示例

展示如何在 Agentic 编排模式下使用 GlobalConfig 来配置节点。

GlobalConfig 的作用：
- 在 Agent 自动生成工作流时，节点会自动从 GlobalConfig 读取配置
- 避免在每个节点创建时手动传递 config 参数
- 特别适合需要统一配置的场景（如数据库连接、文件路径等）

使用场景：
1. 多个节点共享相同的配置（如数据库连接信息）
2. Agent 自动生成的工作流需要访问预配置的资源
3. 简化节点配置管理，提高代码可维护性

环境变量配置：
- DEEPEYE_LLM_API_KEY: LLM API密钥（必需）
- DEEPEYE_LLM_BASE_URL: LLM API基础URL（可选）
- DEEPEYE_LLM_MODEL: LLM模型名称（可选）

Example:
    export DEEPEYE_LLM_API_KEY="sk-..."
    python examples/agent_with_global_config.py
"""

import os
import json
from typing import Optional
from pathlib import Path

from deepeye.llm import LLMClient
from deepeye.agent import PlannerAgent
from deepeye.config import get_global_config

# 导入节点
from deepeye.nodes.datasource import (
    FileDataSourceNode,
    CSVDataSourceNode,
    MemoryDataSourceNode,
)
from deepeye.nodes.processing import (
    FilterNode,
    TransformNode,
)
from deepeye.nodes.datacoder import DataCoderNode
from deepeye.nodes.dataplot import DataPlotNode


def get_env_config() -> dict:
    """从环境变量获取 LLM 配置"""
    api_key = os.getenv("DEEPEYE_LLM_API_KEY")
    if not api_key:
        raise ValueError(
            "未设置环境变量 DEEPEYE_LLM_API_KEY\n"
            "请设置: export DEEPEYE_LLM_API_KEY='your-api-key'"
        )
    
    return {
        "api_key": api_key,
        "base_url": os.getenv("DEEPEYE_LLM_BASE_URL", "https://api.openai.com/v1"),
        "model": os.getenv("DEEPEYE_LLM_MODEL", "gpt-3.5-turbo"),
    }


def setup_global_config():
    """设置全局配置
    
    这里配置所有节点的默认参数。当 Agent 自动创建节点时，
    节点会自动从这里读取配置。
    """
    print("🔧 配置 GlobalConfig...")
    config = get_global_config()
    
    # 清空之前的配置
    config.clear_all()
    
    # 配置文件数据源节点
    # 注意：这里配置的是节点类名，不是工具名
    config.set_node_config("FileDataSource", {
        "file_path": "/tmp/sales_data.csv",  # 默认文件路径
        "encoding": "utf-8",
    })
    
    config.set_node_config("CSVDataSource", {
        "file_path": "/tmp/sales_data.csv",
        "encoding": "utf-8",
    })
    
    # 配置内存数据源（示例数据）
    import pandas as pd
    sample_df = pd.DataFrame({
        "product": ["A", "B", "C", "D", "E"],
        "sales": [1000, 1500, 800, 2000, 1200],
        "region": ["North", "South", "East", "West", "North"],
        "category": ["Electronics", "Clothing", "Food", "Electronics", "Clothing"]
    })
    
    config.set_node_config("MemoryDataSource", {
        "dataframe": sample_df,
        "name": "SampleSalesData"
    })
    
    print("✓ GlobalConfig 配置完成:")
    print(f"  - FileDataSource: file_path=/tmp/sales_data.csv")
    print(f"  - CSVDataSource: file_path=/tmp/sales_data.csv")
    print(f"  - MemoryDataSource: 5 rows sample data")
    print()


def create_agent_with_nodes() -> PlannerAgent:
    """创建 Agent 并注册节点"""
    config = get_env_config()
    
    print("🤖 创建 PlannerAgent...")
    print(f"  LLM Model: {config['model']}")
    print(f"  Base URL: {config['base_url']}")
    
    # 创建 LLM 客户端
    llm_client = LLMClient(
        api_key=config["api_key"],
        base_url=config["base_url"],
        timeout=60,
        max_retries=3,
    )
    
    # 创建 Agent
    agent = PlannerAgent(
        llm_client=llm_client,
        model=config["model"],
        max_retries=3,
        temperature=0.3,
    )
    
    # 注册节点（不需要传递配置，会自动从 GlobalConfig 读取）
    print("\n📋 注册节点...")
    agent.register_node(FileDataSourceNode)
    agent.register_node(CSVDataSourceNode)
    agent.register_node(MemoryDataSourceNode)
    agent.register_node(FilterNode)
    agent.register_node(TransformNode)
    agent.register_node(DataCoderNode)
    agent.register_node(DataPlotNode)
    
    registered_tools = agent.tool_registry.get_tool_names()
    print(f"✓ 已注册 {len(registered_tools)} 个工具:")
    for tool_name in sorted(registered_tools):
        print(f"    - {tool_name}")
    print()
    
    return agent


def example_1_simple_data_analysis():
    """示例1: 简单数据分析
    
    任务：从内存加载数据，筛选销售额大于1000的产品，并显示结果
    
    GlobalConfig 的作用：
    - MemoryDataSource 会自动使用预配置的 DataFrame
    - 无需在任务描述中指定数据内容
    """
    print("=" * 70)
    print("示例1: 使用 GlobalConfig 的简单数据分析")
    print("=" * 70)
    
    # 设置全局配置
    setup_global_config()
    
    # 创建 Agent
    agent = create_agent_with_nodes()
    
    # 定义任务（注意：不需要在任务中指定数据内容）
    task = """
    从内存数据源加载销售数据，
    使用 DataCoder 筛选出销售额（sales）大于 1000 的产品，
    然后按销售额降序排列。
    """
    
    print(f"📝 任务描述:\n{task}\n")
    
    # 运行 Agent（仅生成工作流，不执行）
    print("🚀 开始执行...\n")
    result = agent.run(task, auto_execute=False)
    
    # 输出结果
    print("\n" + "=" * 70)
    print("执行结果")
    print("=" * 70)
    print(f"状态: {result.status.value}")
    print(f"成功: {result.success}")
    
    if result.success:
        print("\n✅ 工作流生成成功!")
        
        if result.workflow:
            print(f"\n📊 工作流信息:")
            print(f"  节点数: {len(result.workflow.list_nodes())}")
            print(f"  节点列表:")
            for node_id in result.workflow.list_nodes():
                node = result.workflow.nodes[node_id]
                print(f"    - {node_id}: {node.__class__.__name__}")
            
            print(f"\n  连接数: {len(result.workflow.get_connections())}")
            if result.workflow.get_connections():
                print(f"  连接列表:")
                for conn in result.workflow.get_connections():
                    print(f"    - {conn}")
        
        if result.plan:
            print(f"\n📋 执行计划:")
            for step in result.plan.get("steps", []):
                print(f"  步骤 {step['step_id']}: {step['description']}")
                print(f"    工具: {step['tool']}")
    else:
        print(f"\n❌ 失败: {result.error}")
    
    # 输出日志
    print(f"\n📜 执行日志:")
    for log in result.logs:
        print(f"  {log}")
    
    return result


def example_2_with_execution():
    """示例2: 完整执行工作流
    
    任务：从内存加载数据并执行完整的数据分析流程
    
    演示：
    - GlobalConfig 配置的数据会在执行时被使用
    - Agent 自动生成并执行工作流
    - 获取最终的执行结果
    """
    print("\n\n")
    print("=" * 70)
    print("示例2: 完整执行工作流（含 GlobalConfig）")
    print("=" * 70)
    
    # 设置全局配置
    setup_global_config()
    
    # 创建 Agent
    agent = create_agent_with_nodes()
    
    # 定义任务
    task = """
    从内存数据源加载销售数据，
    筛选 Electronics 类别的产品，
    统计总销售额。
    """
    
    print(f"📝 任务描述:\n{task}\n")
    
    # 运行 Agent（自动执行）
    print("🚀 开始执行...\n")
    result = agent.run(task, auto_execute=True)
    
    # 输出结果
    print("\n" + "=" * 70)
    print("执行结果")
    print("=" * 70)
    print(f"状态: {result.status.value}")
    print(f"成功: {result.success}")
    
    if result.success:
        print("\n✅ 工作流执行成功!")
        
        if result.execution_result:
            print(f"\n🎯 执行结果:")
            print(json.dumps(result.execution_result, indent=2, ensure_ascii=False))
    else:
        print(f"\n❌ 失败: {result.error}")
    
    # 输出完整日志
    print(f"\n📜 完整日志:")
    for log in result.logs:
        print(f"  {log}")
    
    return result


def example_3_dynamic_override():
    """示例3: 动态覆盖 GlobalConfig
    
    演示如何在特定场景下覆盖全局配置：
    - GlobalConfig 提供默认配置
    - Agent 的 static_inputs 可以覆盖特定参数
    - 两者结合提供最大灵活性
    """
    print("\n\n")
    print("=" * 70)
    print("示例3: GlobalConfig + 动态覆盖")
    print("=" * 70)
    
    # 设置全局配置（默认数据）
    setup_global_config()
    
    # 创建 Agent
    agent = create_agent_with_nodes()
    
    # 任务中可以指定特定的参数，这些参数会通过 static_inputs 传递
    # 从而覆盖 GlobalConfig 中的默认配置
    task = """
    从内存数据源加载销售数据，
    筛选 North 地区的产品，
    计算平均销售额。
    """
    
    print(f"📝 任务描述:\n{task}\n")
    print("💡 说明:")
    print("  - GlobalConfig 提供了默认的 DataFrame")
    print("  - Agent 根据任务需求生成 static_inputs")
    print("  - static_inputs 中的参数会覆盖 GlobalConfig 的默认值")
    print()
    
    # 运行 Agent
    print("🚀 开始执行...\n")
    result = agent.run(task, auto_execute=False)
    
    # 输出结果
    print("\n" + "=" * 70)
    print("执行结果")
    print("=" * 70)
    
    if result.success and result.plan:
        print(f"\n📋 执行计划详情:")
        for step in result.plan.get("steps", []):
            print(f"\n  步骤 {step['step_id']}: {step['description']}")
            print(f"    工具: {step['tool']}")
            
            if step.get('static_inputs'):
                print(f"    静态输入 (覆盖 GlobalConfig):")
                for port, params in step['static_inputs'].items():
                    print(f"      端口 '{port}':")
                    for k, v in params.items():
                        print(f"        {k} = {v}")
            else:
                print(f"    静态输入: 无（使用 GlobalConfig 默认值）")
            
            if step.get('connections'):
                print(f"    连接:")
                for conn in step['connections']:
                    print(f"      从步骤 {conn['from_step']} 的 {conn['from_port']} "
                          f"连接到 {conn['to_port']}")
    
    return result


def main():
    """主函数"""
    print("=" * 70)
    print("🤖 DeepEye Agent + GlobalConfig 集成示例")
    print("=" * 70)
    print()
    print("本示例演示如何使用 GlobalConfig 来简化 Agent 编排中的节点配置。")
    print()
    print("优势：")
    print("  ✅ 节点自动读取 GlobalConfig 中的默认配置")
    print("  ✅ 无需在每个节点创建时手动传递 config")
    print("  ✅ Agent 生成的 static_inputs 可以覆盖默认配置")
    print("  ✅ 提高代码可维护性和配置一致性")
    print()
    
    try:
        # 检查环境变量
        config = get_env_config()
        print("✓ LLM 配置正确\n")
        
        # 选择示例
        print("选择要运行的示例:")
        print("  1. 简单数据分析（仅生成工作流）")
        print("  2. 完整执行工作流")
        print("  3. 动态覆盖 GlobalConfig")
        print("  all. 运行所有示例")
        print()
        
        choice = input("请输入选择 (1/2/3/all) [默认: 1]: ").strip() or "1"
        print()
        
        if choice == "1":
            example_1_simple_data_analysis()
        elif choice == "2":
            example_2_with_execution()
        elif choice == "3":
            example_3_dynamic_override()
        elif choice.lower() == "all":
            example_1_simple_data_analysis()
            example_2_with_execution()
            example_3_dynamic_override()
        else:
            print(f"❌ 无效的选择: {choice}")
            return 1
        
        print("\n" + "=" * 70)
        print("✅ 示例运行完成!")
        print("=" * 70)
        
    except ValueError as e:
        print(f"❌ 配置错误: {e}")
        print("\n请设置以下环境变量:")
        print("  export DEEPEYE_LLM_API_KEY='your-api-key'")
        print("  export DEEPEYE_LLM_BASE_URL='https://api.openai.com/v1'  # 可选")
        print("  export DEEPEYE_LLM_MODEL='gpt-4'  # 可选")
        return 1
    
    except Exception as e:
        print(f"❌ 运行错误: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())


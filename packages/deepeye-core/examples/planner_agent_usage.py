"""Planner Agent 使用示例

展示如何使用 PlannerAgent 从自然语言任务生成并执行工作流。

环境变量配置：
- DEEPEYE_LLM_API_KEY: LLM API密钥（必需）
- DEEPEYE_LLM_BASE_URL: LLM API基础URL（可选，默认OpenAI）
- DEEPEYE_LLM_MODEL: LLM模型名称（可选，默认gpt-3.5-turbo）

Example:
    export DEEPEYE_LLM_API_KEY="sk-..."
    export DEEPEYE_LLM_BASE_URL="https://api.openai.com/v1"
    export DEEPEYE_LLM_MODEL="gpt-4"
    python examples/planner_agent_usage.py
"""

import os
import json
from typing import Optional
import pandas as pd

from deepeye.llm import LLMClient
from deepeye.agent import PlannerAgent
from deepeye.config import get_global_config

# 导入所有可用的节点
from deepeye.nodes.database import DatabaseDataSourceNode
from deepeye.nodes.nl2sql import NL2SQLNode
from deepeye.nodes.datacoder import DataCoderNode
from deepeye.nodes.dataplot import DataPlotNode
from deepeye.nodes.datasource import (
    MemoryDataSourceNode,
    FileDataSourceNode,
    CSVDataSourceNode,
    JSONDataSourceNode,
    ExcelDataSourceNode,
)
from deepeye.nodes.processing import (
    FilterNode,
    RowFilterNode,
    ColumnSelectNode,
    TransformNode,
)


def _print_execution_result(exec_result: dict) -> None:
    """美化打印执行结果
    
    Args:
        exec_result: 工作流执行结果字典，包含：
            - success: bool
            - outputs: dict - 每个节点的输出
            - errors: dict or None - 错误信息
    """
    # 打印整体状态
    if exec_result.get("success"):
        print("  ✅ 状态: 成功")
    else:
        print("  ❌ 状态: 失败")
    
    # 打印错误信息（如果有）
    if exec_result.get("errors"):
        print("\n  ⚠️  错误信息:")
        for node_id, error in exec_result["errors"].items():
            print(f"    • 节点 {node_id}: {error}")
    
    # 打印节点输出
    outputs = exec_result.get("outputs", {})
    if outputs:
        print(f"\n  📤 节点输出 (共 {len(outputs)} 个节点):")
        print("  " + "-" * 56)
        
        for node_id, node_outputs in outputs.items():
            print(f"\n  📍 节点: {node_id}")
            
            if not node_outputs:
                print("    (无输出)")
                continue
            
            for port_name, output_data in node_outputs.items():
                print(f"    🔌 端口: {port_name}")
                
                # 如果 output_data 是字符串（可能是 str(output) 的结果）
                if isinstance(output_data, str):
                    # 完整输出字符串，不限制长度
                    print(f"       {output_data}")
                    continue
                
                # 根据输出类型选择合适的展示方式
                if isinstance(output_data, dict):
                    # 如果是字典，尝试识别特殊类型
                    if "type" in output_data:
                        output_type = output_data.get("type", "unknown")
                        print(f"       类型: {output_type}")
                        
                        # DataFrame 类型
                        if output_type == "dataframe" and "data" in output_data:
                            df_data = output_data["data"]
                            if isinstance(df_data, list) and df_data:
                                print(f"       行数: {len(df_data)}")
                                print(f"       列数: {len(df_data[0]) if df_data else 0}")
                                # 显示所有数据（不限制行数）
                                print("       完整数据:")
                                try:
                                    df = pd.DataFrame(df_data)
                                    print("       " + df.to_string(index=False).replace("\n", "\n       "))
                                except Exception:
                                    print(f"       {json.dumps(df_data, ensure_ascii=False, indent=10)}")
                        
                        # SQL 类型
                        elif output_type == "sql" and "sql" in output_data:
                            print(f"       SQL: {output_data['sql']}")
                        
                        # Chart/图表类型
                        elif output_type in ["chart", "plot", "figure"]:
                            if "path" in output_data:
                                print(f"       文件路径: {output_data['path']}")
                            if "config" in output_data:
                                print(f"       配置: {json.dumps(output_data['config'], ensure_ascii=False)}")
                        
                        # Code 类型
                        elif output_type == "code" and "code" in output_data:
                            code = output_data["code"]
                            # 显示完整代码（不限制行数）
                            print(f"       完整代码:")
                            print("       " + code.replace("\n", "\n       "))
                        
                        # 其他类型
                        else:
                            # 打印其他字段（完整输出，不限制长度）
                            for key, value in output_data.items():
                                if key != "type":
                                    value_str = json.dumps(value, ensure_ascii=False, indent=2) if not isinstance(value, str) else value
                                    print(f"       {key}: {value_str}")
                    else:
                        # 普通字典（完整输出，不限制长度）
                        try:
                            dict_str = json.dumps(output_data, ensure_ascii=False, indent=2)
                            print(f"       {dict_str}")
                        except (TypeError, ValueError):
                            # 如果无法序列化，直接用 str() 显示
                            dict_str = str(output_data)
                            print(f"       {dict_str}")
                
                elif isinstance(output_data, (list, tuple)):
                    print(f"       列表长度: {len(output_data)}")
                    # 完整输出列表，不限制长度
                    if output_data:
                        try:
                            list_str = json.dumps(list(output_data), ensure_ascii=False, indent=2)
                            print(f"       完整列表: {list_str}")
                        except (TypeError, ValueError):
                            print(f"       完整列表: {output_data}")
                
                else:
                    # 其他类型，完整输出不限制长度
                    output_str = str(output_data)
                    print(f"       {output_str}")
        
        print("  " + "-" * 56)
    else:
        print("\n  (无节点输出)")


def get_env_config() -> dict:
    """从环境变量获取配置
    
    Returns:
        配置字典，包含 api_key, base_url, model
        
    Raises:
        ValueError: 如果缺少必需的环境变量
    """
    api_key = os.getenv("DEEPEYE_LLM_API_KEY")
    if not api_key:
        raise ValueError(
            "未设置环境变量 DEEPEYE_LLM_API_KEY\n"
            "请设置: export DEEPEYE_LLM_API_KEY='your-api-key'"
        )
    
    base_url = os.getenv("DEEPEYE_LLM_BASE_URL", "https://api.openai.com/v1")
    model = os.getenv("DEEPEYE_LLM_MODEL", "gpt-3.5-turbo")
    
    return {
        "api_key": api_key,
        "base_url": base_url,
        "model": model,
    }


def setup_global_config():
    """设置全局节点配置
    
    这些配置会被所有创建的节点继承，除非节点在创建时显式覆盖。
    """
    print("🔧 设置全局节点配置...")
    
    global_config = get_global_config()
    
    # 获取示例数据文件的路径（相对于当前脚本）
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(script_dir, "data")
    
    # 配置 FileDataSource 的默认参数和示例文件（通用文件数据源）
    global_config.set_node_config("FileDataSource", {
        "file_path": os.path.join(data_dir, "products.csv"),
        "file_type": "auto",  # 自动检测文件类型
        "encoding": "utf-8",
        "delimiter": ",",
        "allow_remote": True,
    })
    
    # 配置 CSVDataSource 的默认参数和示例文件
    global_config.set_node_config("CSVDataSource", {
        "file_path": os.path.join(data_dir, "employees.csv"),
        "encoding": "utf-8",
        "delimiter": ",",
        "header": 0,
    })
    
    # 配置 ExcelDataSource 的默认参数和示例文件
    global_config.set_node_config("ExcelDataSource", {
        "file_path": os.path.join(data_dir, "company_data.xlsx"),
        "sheet_name": "Employees",  # 默认读取 Employees sheet
        "header": 0,
    })
    
    # 配置 JSONDataSource 的默认参数和示例文件
    global_config.set_node_config("JSONDataSource", {
        "file_path": os.path.join(data_dir, "sales.json"),
        "encoding": "utf-8",
        "orient": "records",
    })
    
    # 配置 Filter 节点的默认参数
    global_config.set_node_config("Filter", {
        "drop_na": False,  # 默认不删除 NA 值
    })
    
    # 配置 MemoryDataSource 的示例数据（用于测试）
    sample_data = pd.DataFrame({
        "id": [1, 2, 3, 4, 5],
        "name": ["Alice", "Bob", "Charlie", "David", "Eve"],
        "age": [25, 30, 35, 40, 45],
        "salary": [50000, 60000, 70000, 80000, 90000],
        "department": ["HR", "IT", "Finance", "IT", "HR"]
    })
    global_config.set_node_config("MemoryDataSource", {
        "data": sample_data,
    })
    
    # 配置使用 LLM 的节点（从环境变量读取）
    # 这些节点包括：DataCoder, DataPlot, NL2SQL
    api_key = os.getenv("DEEPEYE_LLM_API_KEY")
    base_url = os.getenv("DEEPEYE_LLM_BASE_URL", "https://api.openai.com/v1")
    model = os.getenv("DEEPEYE_LLM_MODEL", "gpt-4")
    
    if api_key:
        llm_config = {
            "api_key": api_key,
            "base_url": base_url,
            "model": model,
            "temperature": 0.1,
        }
        
        # 配置 DataCoder 节点
        global_config.set_node_config("DataCoder", llm_config.copy())
        
        # 配置 DataPlot 节点
        global_config.set_node_config("DataPlot", llm_config.copy())
        
        # 配置 NL2SQL 节点
        global_config.set_node_config("NL2SQL", llm_config.copy())
    
    print("  ✓ 已设置默认配置:")
    print(f"    - FileDataSource: {os.path.basename(os.path.join(data_dir, 'products.csv'))} (通用文件数据源)")
    print(f"    - CSVDataSource: {os.path.basename(os.path.join(data_dir, 'employees.csv'))}")
    print(f"    - ExcelDataSource: {os.path.basename(os.path.join(data_dir, 'company_data.xlsx'))} (Employees sheet)")
    print(f"    - JSONDataSource: {os.path.basename(os.path.join(data_dir, 'sales.json'))}")
    print("    - Filter: drop_na=False")
    print("    - MemoryDataSource: 示例员工数据 (5行)")
    if api_key:
        print(f"    - LLM 节点 (DataCoder/DataPlot/NL2SQL):")
        print(f"      • Base URL: {base_url}")
        print(f"      • Model: {model}")
    else:
        print("    - ⚠️  未检测到 DEEPEYE_OPENAI_API_KEY，LLM 节点将无法使用")
        print("      请设置环境变量: DEEPEYE_OPENAI_API_KEY, DEEPEYE_OPENAI_BASE_URL, DEEPEYE_OPENAI_MODEL")
    print()


def create_planner_agent() -> PlannerAgent:
    """创建并配置 PlannerAgent
    
    Returns:
        配置好的 PlannerAgent 实例
    """
    # 设置全局配置
    setup_global_config()
    
    # 获取 LLM 配置
    config = get_env_config()
    
    print("📋 LLM 配置:")
    print(f"  Base URL: {config['base_url']}")
    print(f"  Model: {config['model']}")
    print()
    
    # 创建 LLM 客户端
    llm_client = LLMClient(
        api_key=config["api_key"],
        base_url=config["base_url"],
        timeout=60,
        max_retries=3,
    )
    
    # 创建 Planner Agent
    agent = PlannerAgent(
        llm_client=llm_client,
        model=config["model"],
        max_retries=3,
        temperature=0.3,  # 较低的温度，使输出更确定性
    )
    
    # 注册所有可用的节点
    print("🔧 注册节点...")
    
    # 数据库节点
    # agent.register_node(DatabaseDataSourceNode)
    # agent.register_node(NL2SQLNode)
    
    # 数据处理节点
    agent.register_node(DataCoderNode)
    agent.register_node(DataPlotNode)
    
    # 数据源节点
    agent.register_node(MemoryDataSourceNode)
    agent.register_node(FileDataSourceNode)
    agent.register_node(CSVDataSourceNode)
    agent.register_node(JSONDataSourceNode)
    agent.register_node(ExcelDataSourceNode)
    
    registered_tools = agent.tool_registry.get_tool_names()
    print(f"  ✓ 已注册 {len(registered_tools)} 个节点工具:")
    for tool_name in sorted(registered_tools):
        print(f"    - {tool_name}")
    print()
    
    return agent


def example_1_simple_task():
    """示例1: 简单任务 - 从CSV文件加载数据并分析"""
    print("=" * 60)
    print("示例1: 从CSV文件加载数据并分析")
    print("=" * 60)
    
    # 创建 Agent
    agent = create_planner_agent()
    
    # 定义任务
    task = "从sales.csv文件加载数据，筛选出销售额大于1000的记录，并按销售额降序排列"
    
    print(f"📝 任务: {task}\n")
    
    # 运行 Agent（不自动执行，只生成工作流）
    result = agent.run(task, auto_execute=False)
    
    # 输出结果
    print("\n" + "=" * 60)
    print("执行结果:")
    print("=" * 60)
    print(f"状态: {result.status.value}")
    print(f"成功: {result.success}")
    
    if result.success:
        print("\n✓ 工作流生成成功!")
        
        # 输出执行计划
        if result.plan:
            print("\n📋 执行计划:")
            print(json.dumps(result.plan, indent=2, ensure_ascii=False))
        
        # 输出工作流信息
        if result.workflow:
            print("\n🔄 工作流信息:")
            print(f"  节点数: {len(result.workflow.list_nodes())}")
            print(f"  连接数: {len(result.workflow.get_connections())}")
            print(f"  节点列表: {result.workflow.list_nodes()}")
    else:
        print(f"\n❌ 失败: {result.error}")
    
    # 输出日志
    print("\n📜 执行日志:")
    for log in result.logs:
        print(f"  {log}")
    
    return result


def example_2_database_query():
    """示例2: 数据库查询 - 使用 NL2SQL"""
    print("\n\n")
    print("=" * 60)
    print("示例2: 使用自然语言查询数据库")
    print("=" * 60)
    
    # 创建 Agent
    agent = create_planner_agent()
    
    # 定义任务
    task = (
        "连接到MySQL数据库（主机localhost，用户root，数据库名sales_db），"
        "使用自然语言查询'查询2024年销售额前10的产品'，"
        "然后生成销售额的柱状图"
    )
    
    print(f"📝 任务: {task}\n")
    
    # 运行 Agent（不自动执行）
    result = agent.run(task, auto_execute=False)
    
    # 输出结果
    print("\n" + "=" * 60)
    print("执行结果:")
    print("=" * 60)
    print(f"状态: {result.status.value}")
    print(f"成功: {result.success}")
    
    if result.success:
        print("\n✓ 工作流生成成功!")
        
        # 输出执行计划
        if result.plan:
            print("\n📋 执行计划:")
            for step in result.plan.get("steps", []):
                print(f"  步骤 {step['step_id']}: {step['description']}")
                print(f"    工具: {step['tool']}")
                if step.get('connections'):
                    print(f"    连接: {step['connections']}")
                if step.get('static_inputs'):
                    print(f"    静态输入: {step['static_inputs']}")
    else:
        print(f"\n❌ 失败: {result.error}")
    
    # 输出日志
    print("\n📜 执行日志:")
    for log in result.logs:
        print(f"  {log}")
    
    return result


def example_3_complex_pipeline():
    """示例3: 复杂数据处理流水线"""
    print("\n\n")
    print("=" * 60)
    print("示例3: 复杂数据处理流水线")
    print("=" * 60)
    
    # 创建 Agent
    agent = create_planner_agent()
    
    # 定义任务
    task = (
        "1. 从Excel文件'customer_data.xlsx'加载客户数据，"
        "2. 使用DataCoder筛选出年龄大于30岁且消费金额大于5000的客户，"
        "3. 使用DataCoder计算每个客户的平均消费金额，"
        "4. 生成消费金额分布的直方图"
    )
    
    print(f"📝 任务: {task}\n")
    
    # 运行 Agent（不自动执行）
    result = agent.run(task, auto_execute=False)
    
    # 输出结果
    print("\n" + "=" * 60)
    print("执行结果:")
    print("=" * 60)
    print(f"状态: {result.status.value}")
    print(f"成功: {result.success}")
    
    if result.success:
        print("\n✓ 工作流生成成功!")
        
        # 输出工作流信息
        if result.workflow:
            print("\n🔄 工作流结构:")
            print(f"  节点: {result.workflow.list_nodes()}")
            print(f"  连接:")
            for conn in result.workflow.get_connections():
                print(f"    {conn}")
            
            # 输出工作流 JSON
            workflow_json = result.workflow.to_json()
            print(f"\n📄 工作流 JSON (前500字符):")
            print(workflow_json[:500] + "...")
    else:
        print(f"\n❌ 失败: {result.error}")
    
    return result


def example_4_with_execution():
    """示例4: 完整执行 - 生成并执行工作流（使用全局配置的数据）"""
    print("\n\n")
    print("=" * 60)
    print("示例4: 完整执行工作流（使用全局配置）")
    print("=" * 60)
    
    # 创建 Agent（会自动设置全局配置）
    agent = create_planner_agent()
    
    # 定义一个简单的任务（使用全局配置中的示例数据）
    task = "从内存数据源加载示例数据，筛选出 IT 部门的员工，并计算他们的平均薪资"
    
    print(f"📝 任务: {task}\n")
    print("💡 提示: 这个任务会使用全局配置中预设的员工数据\n")
    
    # 运行 Agent（自动执行）
    result = agent.run(task, auto_execute=True)
    
    # 输出结果
    print("\n" + "=" * 60)
    print("执行结果:")
    print("=" * 60)
    print(f"状态: {result.status.value}")
    print(f"成功: {result.success}")
    
    # 打印生成的 workflow JSON
    # 输出工作流信息
    if result.workflow:
        print("\n🔄 工作流结构:")
        print(f"  节点: {result.workflow.list_nodes()}")
        print(f"  连接:")
        for conn in result.workflow.get_connections():
            print(f"    {conn}")
    
    if result.success:
        print("\n✓ 工作流执行成功!")
        
        # 输出执行结果
        if result.execution_result:
            print("\n🎯 执行结果:")
            _print_execution_result(result.execution_result)
    else:
        print(f"\n❌ 失败: {result.error}")
    
    # 输出完整日志
    print("\n📜 完整日志:")
    for log in result.logs:
        print(f"  {log}")
    
    return result


def example_5_global_config_demo():
    """示例5: 演示全局配置的使用"""
    print("\n\n")
    print("=" * 60)
    print("示例5: 全局配置使用演示")
    print("=" * 60)
    
    # 首先设置全局配置
    setup_global_config()
    
    # 访问全局配置
    global_config = get_global_config()
    
    # 查看预设的内存数据
    memory_config = global_config.get_node_config("MemoryDataSource")
    if memory_config and "data" in memory_config:
        sample_df = memory_config["data"]
        print("\n📊 MemoryDataSource 全局配置中的示例数据:")
        print(sample_df.to_string(index=False))
        print(f"\n  形状: {sample_df.shape}")
        print(f"  列: {list(sample_df.columns)}")
    
    # 查看文件数据源的配置
    print("\n📁 文件数据源的全局配置:")
    
    # FileDataSource（通用文件数据源）
    file_config = global_config.get_node_config("FileDataSource")
    if file_config and "file_path" in file_config:
        file_path = file_config["file_path"]
        file_type = file_config.get("file_type", "auto")
        print(f"\n  FileDataSource (通用):")
        print(f"    文件: {os.path.basename(file_path)}")
        print(f"    路径: {file_path}")
        print(f"    类型: {file_type}")
        print(f"    存在: {os.path.exists(file_path)}")
        if os.path.exists(file_path):
            # 读取并预览数据
            try:
                df = pd.read_csv(file_path)
                print(f"    形状: {df.shape}")
                print(f"    列: {list(df.columns)}")
                print("\n    前3行数据:")
                print("    " + "\n    ".join(df.head(3).to_string(index=False).split("\n")))
            except Exception as e:
                print(f"    读取错误: {e}")
    
    csv_config = global_config.get_node_config("CSVDataSource")
    if csv_config and "file_path" in csv_config:
        csv_path = csv_config["file_path"]
        print(f"\n  CSVDataSource:")
        print(f"    文件: {os.path.basename(csv_path)}")
        print(f"    路径: {csv_path}")
        print(f"    存在: {os.path.exists(csv_path)}")
        if os.path.exists(csv_path):
            # 读取并预览数据
            try:
                df = pd.read_csv(csv_path)
                print(f"    形状: {df.shape}")
                print(f"    列: {list(df.columns)}")
                print("\n    前3行数据:")
                print("    " + "\n    ".join(df.head(3).to_string(index=False).split("\n")))
            except Exception as e:
                print(f"    读取错误: {e}")
    
    excel_config = global_config.get_node_config("ExcelDataSource")
    if excel_config and "file_path" in excel_config:
        excel_path = excel_config["file_path"]
        sheet_name = excel_config.get("sheet_name", 0)
        print(f"\n  ExcelDataSource:")
        print(f"    文件: {os.path.basename(excel_path)}")
        print(f"    路径: {excel_path}")
        print(f"    Sheet: {sheet_name}")
        print(f"    存在: {os.path.exists(excel_path)}")
        if os.path.exists(excel_path):
            # 读取并预览数据
            try:
                df = pd.read_excel(excel_path, sheet_name=sheet_name)
                print(f"    形状: {df.shape}")
                print(f"    列: {list(df.columns)}")
                print("\n    前3行数据:")
                print("    " + "\n    ".join(df.head(3).to_string(index=False).split("\n")))
            except Exception as e:
                print(f"    读取错误: {e}")
    
    json_config = global_config.get_node_config("JSONDataSource")
    if json_config and "file_path" in json_config:
        json_path = json_config["file_path"]
        print(f"\n  JSONDataSource:")
        print(f"    文件: {os.path.basename(json_path)}")
        print(f"    路径: {json_path}")
        print(f"    存在: {os.path.exists(json_path)}")
        if os.path.exists(json_path):
            # 读取并预览数据
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if isinstance(data, list):
                    print(f"    记录数: {len(data)}")
                    if len(data) > 0:
                        print(f"    字段: {list(data[0].keys())}")
                        print("\n    前2条记录:")
                        for i, record in enumerate(data[:2]):
                            print(f"      [{i+1}] {json.dumps(record, ensure_ascii=False)}")
                else:
                    print(f"    类型: {type(data).__name__}")
            except Exception as e:
                print(f"    读取错误: {e}")
    
    # 展示如何动态修改配置
    print("\n🔧 动态修改全局配置:")
    print("  添加新的 RowFilter 配置...")
    global_config.set_node_config("RowFilter", {
        "keep_null": True,
        "case_sensitive": False,
    })
    print("  ✓ 配置已更新")
    
    # 查看所有节点配置（简化显示）
    print("\n📋 当前所有节点的全局配置汇总:")
    all_configs = {
        "FileDataSource": global_config.get_node_config("FileDataSource"),
        "CSVDataSource": global_config.get_node_config("CSVDataSource"),
        "ExcelDataSource": global_config.get_node_config("ExcelDataSource"),
        "JSONDataSource": global_config.get_node_config("JSONDataSource"),
        "MemoryDataSource": global_config.get_node_config("MemoryDataSource"),
        "Filter": global_config.get_node_config("Filter"),
        "RowFilter": global_config.get_node_config("RowFilter"),
    }
    
    for node_type, config in all_configs.items():
        if config:
            # 简化显示：只显示关键信息
            display_items = []
            for k, v in config.items():
                if isinstance(v, pd.DataFrame):
                    display_items.append(f"{k}=<DataFrame {v.shape}>")
                elif k == "file_path":
                    display_items.append(f"{k}={os.path.basename(v)}")
                else:
                    display_items.append(f"{k}={v}")
            print(f"  {node_type}: {', '.join(display_items)}")
    
    print("\n💡 提示: 这些配置会被所有新创建的节点自动继承！")
    print("   可以在创建节点时通过 config 参数覆盖这些默认值。")
    
    return None


def main():
    """主函数"""
    print("=" * 60)
    print("🤖 DeepEye Planner Agent 使用示例")
    print("=" * 60)
    print()
    
    try:
        # 检查环境变量
        config = get_env_config()
        print("✓ 环境变量配置正确\n")
        
        # 运行示例
        print("选择要运行的示例:")
        print("  1. 简单任务 - CSV文件加载和筛选")
        print("  2. 数据库查询 - 使用 NL2SQL")
        print("  3. 复杂流水线 - 多步骤数据处理")
        print("  4. 完整执行 - 生成并执行工作流")
        print("  5. 全局配置演示 - 查看和修改全局配置")
        print("  all. 运行所有示例")
        print()
        
        choice = input("请输入选择 (1/2/3/4/5/all) [默认: 5]: ").strip() or "5"
        
        if choice == "1":
            example_1_simple_task()
        elif choice == "2":
            example_2_database_query()
        elif choice == "3":
            example_3_complex_pipeline()
        elif choice == "4":
            example_4_with_execution()
        elif choice == "5":
            example_5_global_config_demo()
        elif choice.lower() == "all":
            example_1_simple_task()
            example_2_database_query()
            example_3_complex_pipeline()
            example_4_with_execution()
            example_5_global_config_demo()
        else:
            print(f"无效的选择: {choice}")
            return
        
        print("\n" + "=" * 60)
        print("✓ 示例运行完成!")
        print("=" * 60)
        
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


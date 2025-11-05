"""FilterNode使用示例

展示如何使用FilterNode进行数据过滤和列选择。
"""

import pandas as pd
from pathlib import Path

from deepeye import Workflow, WorkflowExecutor
from deepeye.nodes.datasource import CSVDataSource
from deepeye.nodes.processing import FilterNode, RowFilterNode, ColumnSelectNode

# 测试数据目录
EXAMPLES_DIR = Path(__file__).parent
PROJECT_ROOT = EXAMPLES_DIR.parent
TEST_DATA_DIR = PROJECT_ROOT / "tests" / "test_data"


def example_1_simple_row_filter():
    """示例1: 简单的行过滤"""
    print("=" * 60)
    print("示例1: 简单的行过滤")
    print("=" * 60)
    
    csv_file = TEST_DATA_DIR / "sample.csv"
    
    # 读取数据
    source = CSVDataSource(node_id="source", file_path=str(csv_file))
    source_result = source.run(inputs={})
    df = source_result["data"].data
    
    print(f"\n原始数据 ({len(df)}行):")
    print(df)
    
    # 过滤：年龄大于27
    filter_node = FilterNode(
        node_id="filter",
        condition="age > 27"
    )
    
    from deepeye.nodes.io import NodeInput
    filter_result = filter_node.run(inputs={"data": NodeInput(data=df)})
    filtered_df = filter_result["data"].data
    metadata = filter_result["data"].metadata
    
    print(f"\n过滤后数据 (age > 27):")
    print(filtered_df)
    print(f"\n过滤信息:")
    print(f"  原始行数: {metadata['original_shape'][0]}")
    print(f"  结果行数: {metadata['result_shape'][0]}")
    print(f"  过滤掉: {metadata['rows_filtered']}行 ({metadata['filter_rate']:.1%})")
    print()


def example_2_multiple_conditions():
    """示例2: 多条件过滤"""
    print("=" * 60)
    print("示例2: 多条件过滤")
    print("=" * 60)
    
    csv_file = TEST_DATA_DIR / "sample.csv"
    source = CSVDataSource(node_id="source", file_path=str(csv_file))
    df = source.run(inputs={})["data"].data
    
    print(f"\n原始数据:")
    print(df[["name", "age", "city", "score"]])
    
    # AND条件
    filter_and = FilterNode(
        node_id="filter",
        condition="age > 25 and score >= 90"
    )
    
    from deepeye.nodes.io import NodeInput
    result_and = filter_and.run(inputs={"data": NodeInput(data=df)})
    df_and = result_and["data"].data
    
    print(f"\n条件1: age > 25 AND score >= 90")
    print(df_and[["name", "age", "score"]])
    
    # OR条件
    filter_or = FilterNode(
        node_id="filter",
        condition="age < 27 or age > 30"
    )
    result_or = filter_or.run(inputs={"data": NodeInput(data=df)})
    df_or = result_or["data"].data
    
    print(f"\n条件2: age < 27 OR age > 30")
    print(df_or[["name", "age"]])
    print()


def example_3_column_selection():
    """示例3: 列选择"""
    print("=" * 60)
    print("示例3: 列选择")
    print("=" * 60)
    
    csv_file = TEST_DATA_DIR / "sample.csv"
    source = CSVDataSource(node_id="source", file_path=str(csv_file))
    df = source.run(inputs={})["data"].data
    
    print(f"\n原始列: {list(df.columns)}")
    
    # 选择特定列
    filter_node = FilterNode(
        node_id="select",
        columns=["name", "score"]
    )
    
    from deepeye.nodes.io import NodeInput
    result = filter_node.run(inputs={"data": NodeInput(data=df)})
    selected_df = result["data"].data
    
    print(f"选择列: ['name', 'score']")
    print(f"\n结果数据:")
    print(selected_df)
    print()


def example_4_filter_and_select():
    """示例4: 同时过滤行和选择列"""
    print("=" * 60)
    print("示例4: 同时过滤行和选择列")
    print("=" * 60)
    
    csv_file = TEST_DATA_DIR / "sample.csv"
    source = CSVDataSource(node_id="source", file_path=str(csv_file))
    df = source.run(inputs={})["data"].data
    
    print(f"\n原始数据:")
    print(df)
    
    # 过滤并选择
    filter_node = FilterNode(
        node_id="filter_select",
        condition="score >= 90",
        columns=["name", "city", "score"]
    )
    
    from deepeye.nodes.io import NodeInput
    result = filter_node.run(inputs={"data": NodeInput(data=df)})
    result_df = result["data"].data
    
    print(f"\n过滤条件: score >= 90")
    print(f"选择列: ['name', 'city', 'score']")
    print(f"\n结果:")
    print(result_df)
    print()


def example_5_workflow_integration():
    """示例5: 在工作流中使用（完整流程）"""
    print("=" * 60)
    print("示例5: 完整的数据处理工作流")
    print("=" * 60)
    
    csv_file = TEST_DATA_DIR / "sample.csv"
    
    # 创建工作流: 数据源 -> 过滤 -> 列选择
    workflow = Workflow(name="data_filter", workflow_id="demo")
    
    # 节点1: 数据源
    source = CSVDataSource(node_id="source", file_path=str(csv_file))
    
    # 节点2: 过滤高分学生
    filter_high_score = FilterNode(
        node_id="filter_score",
        condition="score >= 90"
    )
    
    # 节点3: 选择关键列
    select_columns = FilterNode(
        node_id="select_cols",
        columns=["name", "score"]
    )
    
    # 添加节点到工作流
    workflow.add_node("source", source)
    workflow.add_node("filter", filter_high_score)
    workflow.add_node("select", select_columns)
    
    # 连接节点
    workflow.add_connection("source", "filter", "data", "data")
    workflow.add_connection("filter", "select", "data", "data")
    
    print("\n工作流结构:")
    print("  数据源 -> 过滤(score>=90) -> 列选择(name,score)")
    
    # 执行工作流
    print("\n执行工作流...")
    executor = WorkflowExecutor(workflow)
    result = executor.execute()
    
    print(f"✅ 工作流执行成功！状态: {result.status.value}")
    
    # 查看各节点的输出
    print("\n各节点输出:")
    
    source_result = result.get_node_result("source")
    source_df = source_result.outputs["data"].data
    print(f"\n1. 数据源输出 ({len(source_df)}行):")
    print(source_df)
    
    filter_result = result.get_node_result("filter")
    filter_df = filter_result.outputs["data"].data
    print(f"\n2. 过滤后输出 ({len(filter_df)}行):")
    print(filter_df)
    
    select_result = result.get_node_result("select")
    final_df = select_result.outputs["data"].data
    print(f"\n3. 最终输出 ({len(final_df)}行, {len(final_df.columns)}列):")
    print(final_df)
    print()


def example_6_convenience_classes():
    """示例6: 使用便捷类"""
    print("=" * 60)
    print("示例6: 使用便捷类")
    print("=" * 60)
    
    csv_file = TEST_DATA_DIR / "sample.csv"
    source = CSVDataSource(node_id="source", file_path=str(csv_file))
    df = source.run(inputs={})["data"].data
    
    print(f"\n原始数据:")
    print(df)
    
    # 使用RowFilterNode（只过滤行）
    print(f"\n使用 RowFilterNode (只过滤行):")
    row_filter = RowFilterNode(
        node_id="row_filter",
        condition="city == 'Beijing'"
    )
    
    from deepeye.nodes.io import NodeInput
    result = row_filter.run(inputs={"data": NodeInput(data=df)})
    filtered_df = result["data"].data
    print(filtered_df)
    
    # 使用ColumnSelectNode（只选择列）
    print(f"\n使用 ColumnSelectNode (只选择列):")
    col_select = ColumnSelectNode(
        node_id="col_select",
        columns=["name", "age"]
    )
    result2 = col_select.run(inputs={"data": NodeInput(data=df)})
    selected_df = result2["data"].data
    print(selected_df)
    print()


def example_7_advanced_conditions():
    """示例7: 高级条件表达式"""
    print("=" * 60)
    print("示例7: 高级条件表达式")
    print("=" * 60)
    
    csv_file = TEST_DATA_DIR / "sample.csv"
    source = CSVDataSource(node_id="source", file_path=str(csv_file))
    df = source.run(inputs={})["data"].data
    
    print(f"\n原始数据:")
    print(df)
    
    # 复杂条件
    filter_node = FilterNode(
        node_id="complex",
        condition="(age > 25 and score >= 90) or city == 'Shanghai'"
    )
    
    from deepeye.nodes.io import NodeInput
    result = filter_node.run(inputs={"data": NodeInput(data=df)})
    result_df = result["data"].data
    
    print(f"\n复杂条件: (age > 25 and score >= 90) or city == 'Shanghai'")
    print(f"结果 ({len(result_df)}行):")
    print(result_df)
    print()


def main():
    """运行所有示例"""
    print("\n")
    print("🚀 DeepEye FilterNode 使用示例")
    print("=" * 60)
    print()
    
    # 检查测试数据
    if not TEST_DATA_DIR.exists():
        print(f"❌ 测试数据目录不存在: {TEST_DATA_DIR}")
        print("请先运行测试生成测试数据")
        return
    
    # 运行所有示例
    example_1_simple_row_filter()
    example_2_multiple_conditions()
    example_3_column_selection()
    example_4_filter_and_select()
    example_5_workflow_integration()
    example_6_convenience_classes()
    example_7_advanced_conditions()
    
    print("=" * 60)
    print("✅ 所有示例运行完成！")
    print("\n💡 关键要点:")
    print("  1. FilterNode主要用于行过滤（使用pandas.query语法）")
    print("  2. 支持可选的列选择功能")
    print("  3. 可以组合复杂的条件表达式（AND, OR）")
    print("  4. 便捷类：RowFilterNode（只过滤行）, ColumnSelectNode（只选择列）")
    print("  5. 在工作流中可以串联多个FilterNode")
    print("  6. 输出包含详细的metadata（过滤率、行数变化等）")
    print()


if __name__ == "__main__":
    main()


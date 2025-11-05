"""端到端完整示例

展示DeepEye的完整数据处理流程：
数据源 → 过滤 → 转换 → 结果展示
"""

from pathlib import Path
import pandas as pd

from deepeye import Workflow, WorkflowExecutor
from deepeye.nodes.datasource import MemoryDataSource, CSVDataSource
from deepeye.nodes.processing import FilterNode, TransformNode
from deepeye.runtime import ExecutionStatus


# 测试数据目录
EXAMPLES_DIR = Path(__file__).parent
PROJECT_ROOT = EXAMPLES_DIR.parent
TEST_DATA_DIR = PROJECT_ROOT / "tests" / "test_data"


def create_sample_sales_data():
    """创建示例销售数据"""
    return pd.DataFrame({
        "date": ["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05",
                 "2024-01-06", "2024-01-07", "2024-01-08"],
        "product": ["iPhone", "iPad", "MacBook", "AirPods", "iPhone", "iPad", "MacBook", "AirPods"],
        "region": ["North", "South", "East", "West", "North", "South", "East", "West"],
        "quantity": [5, 3, 2, 10, 4, 5, 1, 8],
        "unit_price": [799, 599, 1299, 249, 799, 599, 1299, 249],
        "discount_rate": [0.1, 0.05, 0.0, 0.15, 0.08, 0.10, 0.05, 0.12],
    })


def demo_1_simple_pipeline():
    """示例1: 简单的数据处理流水线"""
    print("=" * 80)
    print("示例1: 简单的数据处理流水线")
    print("=" * 80)
    print("\n场景: 销售数据分析")
    print("流程: 读取数据 → 过滤高价值订单 → 计算利润\n")
    
    # 准备数据
    df = create_sample_sales_data()
    
    # 创建工作流
    workflow = Workflow(name="sales_analysis", workflow_id="demo1")
    
    # 节点1: 数据源
    source = MemoryDataSource(node_id="source", data=df)
    
    # 节点2: 过滤 - 只保留数量大于3的订单
    filter_node = FilterNode(
        node_id="filter",
        condition="quantity > 3"
    )
    
    # 节点3: 转换 - 计算收入和利润
    transform = TransformNode(
        node_id="transform",
        add_columns={
            "revenue": "quantity * unit_price * (1 - discount_rate)",
            "profit": "quantity * unit_price * (1 - discount_rate) * 0.3"  # 假设30%利润率
        }
    )
    
    # 构建工作流
    workflow.add_node("source", source)
    workflow.add_node("filter", filter_node)
    workflow.add_node("transform", transform)
    
    workflow.add_connection("source", "filter", "data", "data")
    workflow.add_connection("filter", "transform", "data", "data")
    
    # 执行工作流
    print("📊 执行工作流...")
    executor = WorkflowExecutor(workflow)
    result = executor.execute()
    
    if result.status == ExecutionStatus.SUCCESS:
        print(f"✅ 工作流执行成功！")
        
        # 获取各阶段结果
        source_df = result.get_node_result("source").outputs["data"].data
        filtered_df = result.get_node_result("filter").outputs["data"].data
        final_df = result.get_node_result("transform").outputs["data"].data
        
        print(f"\n📈 数据处理流程:")
        print(f"  原始数据: {len(source_df)}行")
        print(f"  过滤后: {len(filtered_df)}行 (过滤掉{len(source_df) - len(filtered_df)}行)")
        print(f"  最终结果: {len(final_df)}行, {len(final_df.columns)}列")
        
        print(f"\n💰 最终结果:")
        print(final_df[["product", "region", "quantity", "revenue", "profit"]])
        
        print(f"\n📊 汇总统计:")
        print(f"  总收入: ${final_df['revenue'].sum():,.2f}")
        print(f"  总利润: ${final_df['profit'].sum():,.2f}")
    else:
        print(f"❌ 工作流执行失败: {result.status}")
    
    print()


def demo_2_complex_pipeline():
    """示例2: 复杂的数据处理流水线"""
    print("=" * 80)
    print("示例2: 复杂的数据处理流水线")
    print("=" * 80)
    print("\n场景: 销售数据深度分析")
    print("流程: 数据源 → 添加计算列 → 过滤 → 列选择 → 重命名\n")
    
    df = create_sample_sales_data()
    
    # 创建工作流
    workflow = Workflow(name="complex_analysis", workflow_id="demo2")
    
    # 节点1: 数据源
    source = MemoryDataSource(node_id="source", data=df)
    
    # 节点2: 添加计算列
    add_metrics = TransformNode(
        node_id="add_metrics",
        add_columns={
            "revenue": "quantity * unit_price * (1 - discount_rate)",
            "original_price": "quantity * unit_price",
            "discount_amount": "quantity * unit_price * discount_rate"
        }
    )
    
    # 节点3: 过滤高价值订单
    filter_high_value = FilterNode(
        node_id="filter",
        condition="revenue > 2000"
    )
    
    # 节点4: 选择关键列并重命名
    cleanup = TransformNode(
        node_id="cleanup",
        rename_columns={
            "unit_price": "price",
            "discount_rate": "discount"
        },
        drop_columns=["date"]  # 删除不需要的列
    )
    
    # 构建工作流
    workflow.add_node("source", source)
    workflow.add_node("add_metrics", add_metrics)
    workflow.add_node("filter", filter_high_value)
    workflow.add_node("cleanup", cleanup)
    
    workflow.add_connection("source", "add_metrics", "data", "data")
    workflow.add_connection("add_metrics", "filter", "data", "data")
    workflow.add_connection("filter", "cleanup", "data", "data")
    
    # 执行
    print("📊 执行复杂工作流...")
    executor = WorkflowExecutor(workflow)
    result = executor.execute()
    
    if result.is_success():
        print(f"✅ 工作流执行成功！")
        
        # 展示最终结果
        final_df = result.get_node_result("cleanup").outputs["data"].data
        
        print(f"\n💎 高价值订单 (revenue > $2000):")
        print(final_df)
        
        print(f"\n📊 统计:")
        print(f"  订单数: {len(final_df)}")
        print(f"  总收入: ${final_df['revenue'].sum():,.2f}")
        print(f"  平均折扣: {final_df['discount'].mean():.1%}")
    
    print()


def demo_3_csv_to_analysis():
    """示例3: 从CSV文件到完整分析"""
    print("=" * 80)
    print("示例3: 从CSV文件到完整分析")
    print("=" * 80)
    print("\n场景: 学生成绩分析")
    print("流程: CSV文件 → 过滤 → 添加等级 → 统计\n")
    
    csv_file = TEST_DATA_DIR / "sample.csv"
    
    if not csv_file.exists():
        print(f"⚠️  测试数据文件不存在: {csv_file}")
        print("请先运行测试生成数据")
        return
    
    # 创建工作流
    workflow = Workflow(name="student_analysis", workflow_id="demo3")
    
    # 节点1: 读取CSV
    source = CSVDataSource(node_id="source", file_path=str(csv_file))
    
    # 节点2: 过滤成年学生
    filter_adult = FilterNode(
        node_id="filter_adult",
        condition="age >= 27"
    )
    
    # 节点3: 添加成绩等级
    add_grade = TransformNode(
        node_id="add_grade",
        add_columns={
            "grade": "(score // 10) * 10",  # 分数段
            "performance": "score * 1.0"    # 用于后续计算
        }
    )
    
    # 节点4: 清理和重命名
    finalize = TransformNode(
        node_id="finalize",
        rename_columns={"score": "final_score"},
        drop_columns=["performance"]
    )
    
    # 构建工作流
    workflow.add_node("source", source)
    workflow.add_node("filter", filter_adult)
    workflow.add_node("grade", add_grade)
    workflow.add_node("finalize", finalize)
    
    workflow.add_connection("source", "filter", "data", "data")
    workflow.add_connection("filter", "grade", "data", "data")
    workflow.add_connection("grade", "finalize", "data", "data")
    
    # 执行
    print("📊 执行分析工作流...")
    executor = WorkflowExecutor(workflow)
    result = executor.execute()
    
    if result.is_success():
        print(f"✅ 工作流执行成功！")
        
        # 获取结果
        source_df = result.get_node_result("source").outputs["data"].data
        final_df = result.get_node_result("finalize").outputs["data"].data
        
        print(f"\n👨‍🎓 学生分析结果:")
        print(f"  原始学生数: {len(source_df)}")
        print(f"  成年学生数: {len(final_df)}")
        
        print(f"\n📋 成年学生详情:")
        print(final_df[["name", "age", "city", "final_score", "grade"]])
        
        print(f"\n📊 统计:")
        print(f"  平均年龄: {final_df['age'].mean():.1f}岁")
        print(f"  平均分数: {final_df['final_score'].mean():.1f}分")
        print(f"  最高分: {final_df['final_score'].max()}分")
    
    print()


def demo_4_execution_layers():
    """示例4: 查看执行层级（并行潜力）"""
    print("=" * 80)
    print("示例4: 工作流执行层级分析")
    print("=" * 80)
    print("\n展示工作流的执行层级，为未来并行执行做准备\n")
    
    df = create_sample_sales_data()
    
    # 创建一个有分支的工作流
    workflow = Workflow(name="parallel_potential", workflow_id="demo4")
    
    # 数据源
    source = MemoryDataSource(node_id="source", data=df)
    
    # 分支1: 高价值产品分析
    filter_high = FilterNode(node_id="filter_high", condition="unit_price > 500")
    transform_high = TransformNode(
        node_id="transform_high",
        add_columns={"revenue": "quantity * unit_price"}
    )
    
    # 分支2: 大折扣订单分析
    filter_discount = FilterNode(node_id="filter_discount", condition="discount_rate > 0.1")
    transform_discount = TransformNode(
        node_id="transform_discount",
        add_columns={"saved": "quantity * unit_price * discount_rate"}
    )
    
    # 添加节点
    workflow.add_node("source", source)
    workflow.add_node("filter_high", filter_high)
    workflow.add_node("transform_high", transform_high)
    workflow.add_node("filter_discount", filter_discount)
    workflow.add_node("transform_discount", transform_discount)
    
    # 连接（创建两个独立分支）
    workflow.add_connection("source", "filter_high", "data", "data")
    workflow.add_connection("filter_high", "transform_high", "data", "data")
    workflow.add_connection("source", "filter_discount", "data", "data")
    workflow.add_connection("filter_discount", "transform_discount", "data", "data")
    
    # 执行
    executor = WorkflowExecutor(workflow)
    
    # 获取执行层级
    layers = executor.get_execution_layers()
    
    print("📊 工作流结构:")
    print("         source")
    print("        /      \\")
    print("  filter_high  filter_discount")
    print("       |              |")
    print("  transform_high  transform_discount")
    
    print(f"\n🔄 执行层级 (Layer {len(layers)}层):")
    for i, layer in enumerate(layers, 1):
        print(f"  Layer {i}: {', '.join(layer)}")
        if i > 1:
            print(f"           ↑ 这一层的节点可以并行执行")
    
    # 执行工作流
    result = executor.execute()
    
    if result.is_success():
        print(f"\n✅ 工作流执行成功！")
        print(f"\n执行统计:")
        stats = result.get_statistics()
        print(f"  总节点数: {stats['total_nodes']}")
        print(f"  成功: {stats['successful']}")
        print(f"  总耗时: {result.duration:.3f}秒")
        print(f"  平均节点耗时: {stats['avg_node_duration']:.4f}秒")
        
        print(f"\n💡 提示: Layer 2的节点目前是顺序执行的")
        print(f"    未来实现并行执行后，可以同时运行，提升性能！")
    
    print()


def demo_5_error_handling():
    """示例5: 错误处理和调试"""
    print("=" * 80)
    print("示例5: 错误处理和调试")
    print("=" * 80)
    print("\n展示错误情况下的处理和信息\n")
    
    df = create_sample_sales_data()
    
    # 创建一个会出错的工作流
    workflow = Workflow(name="error_demo", workflow_id="demo5")
    
    source = MemoryDataSource(node_id="source", data=df)
    
    # 故意使用错误的列名
    bad_filter = FilterNode(
        node_id="bad_filter",
        condition="nonexistent_column > 100"
    )
    
    workflow.add_node("source", source)
    workflow.add_node("filter", bad_filter)
    workflow.add_connection("source", "filter", "data", "data")
    
    # 执行
    print("📊 执行包含错误的工作流...")
    executor = WorkflowExecutor(workflow, fail_fast=True)
    result = executor.execute()
    
    if result.is_failed():
        print(f"❌ 工作流执行失败（预期的）")
        
        print(f"\n🔍 错误诊断:")
        print(f"  失败节点: {', '.join(result.get_failed_nodes())}")
        print(f"  成功节点: {', '.join(result.get_successful_nodes())}")
        
        # 获取失败节点的详细信息
        failed_node = result.get_node_result("filter")
        if failed_node:
            print(f"\n📝 失败节点详情:")
            print(f"  节点ID: {failed_node.node_id}")
            print(f"  状态: {failed_node.status.value}")
            print(f"  错误: {failed_node.error}")
        
        print(f"\n💡 调试提示:")
        print(f"  - 检查列名是否正确")
        print(f"  - 查看前一个节点的输出")
        print(f"  - 使用metadata了解数据结构")
    
    print()


def main():
    """运行所有示例"""
    print("\n")
    print("🚀 DeepEye 端到端完整示例")
    print("=" * 80)
    print("\n展示完整的数据处理能力:")
    print("  ✓ 数据源: MemoryDataSource, CSVDataSource")
    print("  ✓ 处理: FilterNode, TransformNode")
    print("  ✓ 执行: WorkflowExecutor")
    print()
    
    # 运行所有示例
    demo_1_simple_pipeline()
    demo_2_complex_pipeline()
    demo_3_csv_to_analysis()
    demo_4_execution_layers()
    demo_5_error_handling()
    
    print("=" * 80)
    print("✅ 所有示例运行完成！")
    print("\n🎯 当前DeepEye能力:")
    print("  ✓ 完整的数据处理流水线")
    print("  ✓ 灵活的节点组合")
    print("  ✓ 强大的工作流引擎")
    print("  ✓ 详细的执行追踪")
    print("  ✓ 完善的错误处理")
    print("\n🚀 下一步: LLM智能数据处理节点！")
    print()


if __name__ == "__main__":
    main()


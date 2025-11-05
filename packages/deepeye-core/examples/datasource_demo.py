"""数据源节点使用示例

展示如何使用MemoryDataSource和其他数据源节点。
"""

import pandas as pd
from deepeye.nodes.datasource import MemoryDataSource


def example_1_from_dict_list():
    """示例1: 从字典列表创建数据源"""
    print("=" * 60)
    print("示例1: 从字典列表创建数据源")
    print("=" * 60)
    
    # 创建数据源
    data = [
        {"name": "Alice", "age": 25, "city": "Beijing", "score": 95},
        {"name": "Bob", "age": 30, "city": "Shanghai", "score": 87},
        {"name": "Charlie", "age": 28, "city": "Beijing", "score": 92},
        {"name": "David", "age": 35, "city": "Shenzhen", "score": 88},
    ]
    
    source = MemoryDataSource(node_id="students", data=data)
    
    # 执行节点
    result = source.run(inputs={})
    
    # 获取输出
    output = result["data"]
    df = output.data
    metadata = output.metadata
    
    print(f"\n✅ 数据加载成功！")
    print(f"状态: {output.status.value}")
    print(f"\n数据内容:")
    print(df)
    print(f"\n数据信息:")
    print(f"  行数: {metadata['rows']}")
    print(f"  列名: {metadata['columns']}")
    print(f"  数据类型: {metadata['dtypes']}")
    print()


def example_2_from_dataframe():
    """示例2: 从DataFrame创建数据源"""
    print("=" * 60)
    print("示例2: 从DataFrame创建数据源")
    print("=" * 60)
    
    # 创建DataFrame
    df = pd.DataFrame({
        "product": ["iPhone", "iPad", "MacBook", "AirPods"],
        "price": [799, 599, 1299, 249],
        "quantity": [100, 150, 50, 200],
    })
    
    # 创建数据源
    source = MemoryDataSource(node_id="products", data=df)
    
    # 执行
    result = source.run(inputs={})
    output_df = result["data"].data
    
    print(f"\n✅ 数据加载成功！")
    print(f"\n原始DataFrame:")
    print(df)
    print(f"\n输出DataFrame:")
    print(output_df)
    print(f"\n两者内容一致: {df.equals(output_df)}")
    print()


def example_3_from_2d_array():
    """示例3: 从二维数组创建数据源"""
    print("=" * 60)
    print("示例3: 从二维数组创建数据源")
    print("=" * 60)
    
    # 二维数组数据
    data = [
        [1, "Alice", 85],
        [2, "Bob", 90],
        [3, "Charlie", 78],
    ]
    columns = ["id", "name", "score"]
    
    # 创建数据源
    source = MemoryDataSource(
        node_id="test_results",
        data=data,
        columns=columns
    )
    
    # 执行
    result = source.run(inputs={})
    df = result["data"].data
    
    print(f"\n✅ 数据加载成功！")
    print(f"\n数据内容:")
    print(df)
    print(f"\n数据类型:")
    print(df.dtypes)
    print()


def example_4_metadata_details():
    """示例4: 查看详细的metadata"""
    print("=" * 60)
    print("示例4: 查看详细的metadata")
    print("=" * 60)
    
    # 创建包含数值数据的数据源
    data = [
        {"date": "2024-01-01", "sales": 1000, "cost": 600},
        {"date": "2024-01-02", "sales": 1500, "cost": 900},
        {"date": "2024-01-03", "sales": 1200, "cost": 700},
        {"date": "2024-01-04", "sales": 1800, "cost": 1000},
        {"date": "2024-01-05", "sales": 2000, "cost": 1100},
    ]
    
    source = MemoryDataSource(node_id="daily_sales", data=data)
    result = source.run(inputs={})
    metadata = result["data"].metadata
    
    print(f"\n✅ 数据加载成功！")
    print(f"\n基础信息:")
    print(f"  数据源类型: {metadata['source_type']}")
    print(f"  数据源类别: {metadata['source_category']}")
    print(f"  行数: {metadata['rows']}")
    print(f"  列名: {metadata['columns']}")
    
    print(f"\n数据预览（前5行）:")
    for i, row in enumerate(metadata['preview']['head'], 1):
        print(f"  {i}. {row}")
    
    print(f"\n数值列统计:")
    if 'numeric_stats' in metadata['preview']:
        stats = metadata['preview']['numeric_stats']
        for col, col_stats in stats.items():
            print(f"  {col}:")
            print(f"    平均值: {col_stats['mean']:.2f}")
            print(f"    最小值: {col_stats['min']:.2f}")
            print(f"    最大值: {col_stats['max']:.2f}")
    print()


def example_5_workflow_usage():
    """示例5: 在工作流中使用（模拟）"""
    print("=" * 60)
    print("示例5: 在工作流中使用数据源")
    print("=" * 60)
    
    # 创建数据源
    data = [
        {"region": "North", "sales": 1000, "expenses": 600},
        {"region": "South", "sales": 1500, "expenses": 900},
        {"region": "East", "sales": 1200, "expenses": 700},
        {"region": "West", "sales": 1800, "expenses": 1000},
    ]
    
    source = MemoryDataSource(node_id="regional_data", data=data)
    
    # 执行数据源节点
    result = source.run(inputs={})
    df = result["data"].data
    
    print(f"\n✅ 步骤1: 数据源加载完成")
    print(df)
    
    # 模拟下游处理节点对数据的处理
    print(f"\n📊 步骤2: 下游节点处理数据")
    
    # 计算利润
    df["profit"] = df["sales"] - df["expenses"]
    print(f"\n计算利润后:")
    print(df)
    
    # 计算总计
    total_sales = df["sales"].sum()
    total_profit = df["profit"].sum()
    profit_margin = (total_profit / total_sales * 100) if total_sales > 0 else 0
    
    print(f"\n📈 步骤3: 生成统计报告")
    print(f"  总销售额: ${total_sales:,.2f}")
    print(f"  总利润: ${total_profit:,.2f}")
    print(f"  利润率: {profit_margin:.2f}%")
    print(f"  最佳区域: {df.loc[df['profit'].idxmax(), 'region']}")
    print()


def example_6_empty_data():
    """示例6: 空数据源"""
    print("=" * 60)
    print("示例6: 空数据源")
    print("=" * 60)
    
    # 创建空数据源
    source = MemoryDataSource(node_id="empty", data=None)
    
    # 执行
    result = source.run(inputs={})
    df = result["data"].data
    metadata = result["data"].metadata
    
    print(f"\n✅ 空数据源创建成功！")
    print(f"DataFrame形状: {df.shape}")
    print(f"行数: {metadata['rows']}")
    print(f"列数: {len(metadata['columns'])}")
    print(f"是否为空: {len(df) == 0}")
    print()


def main():
    """运行所有示例"""
    print("\n")
    print("🚀 DeepEye 数据源节点使用示例")
    print("=" * 60)
    print()
    
    # 运行所有示例
    example_1_from_dict_list()
    example_2_from_dataframe()
    example_3_from_2d_array()
    example_4_metadata_details()
    example_5_workflow_usage()
    example_6_empty_data()
    
    print("=" * 60)
    print("✅ 所有示例运行完成！")
    print("\n💡 关键要点:")
    print("  1. MemoryDataSource 支持多种数据格式")
    print("  2. 所有数据源统一输出 DataFrame")
    print("  3. metadata 提供丰富的数据描述信息")
    print("  4. 数据源是工作流的起点")
    print("  5. 输出格式统一，方便下游节点处理")
    print()


if __name__ == "__main__":
    main()


"""文件数据源使用示例

展示如何使用FileDataSource读取CSV和JSON文件。
"""

from pathlib import Path
from deepeye.nodes.datasource import FileDataSource, CSVDataSource, JSONDataSource

# 测试数据目录
EXAMPLES_DIR = Path(__file__).parent
PROJECT_ROOT = EXAMPLES_DIR.parent
TEST_DATA_DIR = PROJECT_ROOT / "tests" / "test_data"


def example_1_read_csv_basic():
    """示例1: 读取CSV文件（基础）"""
    print("=" * 60)
    print("示例1: 读取CSV文件（基础）")
    print("=" * 60)
    
    # 创建文件数据源
    csv_file = TEST_DATA_DIR / "sample.csv"
    source = FileDataSource(
        node_id="csv_reader",
        file_path=str(csv_file)
    )
    
    # 执行读取
    result = source.run(inputs={})
    output = result["data"]
    df = output.data
    metadata = output.metadata
    
    print(f"\n✅ CSV文件读取成功！")
    print(f"状态: {output.status.value}")
    print(f"文件路径: {metadata['source_info']['file_path']}")
    print(f"\n数据内容:")
    print(df)
    print(f"\n数据信息:")
    print(f"  行数: {metadata['rows']}")
    print(f"  列名: {metadata['columns']}")
    print()


def example_2_read_csv_with_options():
    """示例2: 读取CSV文件（带选项）"""
    print("=" * 60)
    print("示例2: 读取CSV文件（带选项）")
    print("=" * 60)
    
    csv_file = TEST_DATA_DIR / "sample.csv"
    
    # 只读前3行，只选择特定列
    source = FileDataSource(
        node_id="csv_limited",
        file_path=str(csv_file),
        nrows=3,
        usecols=["name", "score"]
    )
    
    result = source.run(inputs={})
    df = result["data"].data
    
    print(f"\n✅ 读取成功！")
    print(f"限制: 前3行, 只选择 ['name', 'score'] 列")
    print(f"\n数据内容:")
    print(df)
    print()


def example_3_csv_datasource_class():
    """示例3: 使用CSVDataSource便捷类"""
    print("=" * 60)
    print("示例3: 使用CSVDataSource便捷类")
    print("=" * 60)
    
    csv_file = TEST_DATA_DIR / "sample.csv"
    
    # 使用便捷类，自动识别为CSV
    source = CSVDataSource(
        node_id="csv",
        file_path=str(csv_file)
    )
    
    result = source.run(inputs={})
    df = result["data"].data
    
    print(f"\n✅ CSVDataSource读取成功！")
    print(f"数据形状: {df.shape}")
    print(f"列名: {list(df.columns)}")
    print()


def example_4_read_json():
    """示例4: 读取JSON文件"""
    print("=" * 60)
    print("示例4: 读取JSON文件")
    print("=" * 60)
    
    json_file = TEST_DATA_DIR / "sample.json"
    
    # 自动检测JSON格式
    source = FileDataSource(
        node_id="json_reader",
        file_path=str(json_file)
    )
    
    result = source.run(inputs={})
    df = result["data"].data
    metadata = result["data"].metadata
    
    print(f"\n✅ JSON文件读取成功！")
    print(f"文件类型: {metadata['source_info']['file_type']}")
    print(f"\n数据内容:")
    print(df)
    print()


def example_5_json_datasource_class():
    """示例5: 使用JSONDataSource便捷类"""
    print("=" * 60)
    print("示例5: 使用JSONDataSource便捷类")
    print("=" * 60)
    
    json_file = TEST_DATA_DIR / "sample.json"
    
    # 使用便捷类
    source = JSONDataSource(
        node_id="json",
        file_path=str(json_file)
    )
    
    result = source.run(inputs={})
    df = result["data"].data
    
    print(f"\n✅ JSONDataSource读取成功！")
    print(f"\n数据内容:")
    print(df)
    print(f"\n数据类型:")
    print(df.dtypes)
    print()


def example_6_workflow_usage():
    """示例6: 在工作流中使用（数据分析场景）"""
    print("=" * 60)
    print("示例6: 数据分析工作流")
    print("=" * 60)
    
    csv_file = TEST_DATA_DIR / "sample.csv"
    
    # 步骤1: 读取数据
    print("\n📊 步骤1: 读取CSV数据")
    source = CSVDataSource(
        node_id="student_data",
        file_path=str(csv_file)
    )
    result = source.run(inputs={})
    df = result["data"].data
    print(f"读取了 {len(df)} 条学生数据")
    
    # 步骤2: 数据过滤（模拟FilterNode）
    print("\n🔍 步骤2: 过滤高分学生（score >= 90）")
    high_scorers = df[df["score"] >= 90]
    print(f"找到 {len(high_scorers)} 名高分学生:")
    print(high_scorers[["name", "score"]])
    
    # 步骤3: 数据聚合（模拟AggregateNode）
    print("\n📈 步骤3: 按城市统计")
    city_stats = df.groupby("city").agg({
        "age": "mean",
        "score": ["mean", "count"]
    }).round(2)
    print(city_stats)
    
    # 步骤4: 生成报告
    print("\n📝 步骤4: 生成报告")
    print(f"  总人数: {len(df)}")
    print(f"  平均年龄: {df['age'].mean():.1f}岁")
    print(f"  平均分数: {df['score'].mean():.1f}分")
    print(f"  最高分: {df['score'].max()}分 ({df.loc[df['score'].idxmax(), 'name']})")
    print(f"  城市数: {df['city'].nunique()}")
    print()


def example_7_error_handling():
    """示例7: 错误处理"""
    print("=" * 60)
    print("示例7: 错误处理示例")
    print("=" * 60)
    
    # 文件不存在
    print("\n测试1: 文件不存在")
    source = FileDataSource(
        node_id="test",
        file_path="nonexistent.csv"
    )
    result = source.run(inputs={})
    
    if result["data"].status.value == "failed":
        print(f"❌ 预期的错误: {result['data'].error}")
    
    # 不支持的文件类型
    print("\n测试2: 不支持的文件类型")
    try:
        source = FileDataSource(
            node_id="test",
            file_path="data.txt"  # 不支持的格式
        )
        result = source.run(inputs={})
    except ValueError as e:
        print(f"❌ 预期的错误: {e}")
    
    print()


def main():
    """运行所有示例"""
    print("\n")
    print("🚀 DeepEye 文件数据源使用示例")
    print("=" * 60)
    print()
    
    # 检查测试数据是否存在
    if not TEST_DATA_DIR.exists():
        print(f"❌ 测试数据目录不存在: {TEST_DATA_DIR}")
        print("请先运行测试生成测试数据")
        return
    
    # 运行所有示例
    example_1_read_csv_basic()
    example_2_read_csv_with_options()
    example_3_csv_datasource_class()
    example_4_read_json()
    example_5_json_datasource_class()
    example_6_workflow_usage()
    example_7_error_handling()
    
    print("=" * 60)
    print("✅ 所有示例运行完成！")
    print("\n💡 关键要点:")
    print("  1. FileDataSource 自动检测文件类型（CSV/JSON/Excel）")
    print("  2. 支持本地文件和URL读取")
    print("  3. 内存保护机制（nrows限制）")
    print("  4. 灵活的读取选项（列选择、编码等）")
    print("  5. 便捷类（CSVDataSource, JSONDataSource）")
    print("  6. 统一的DataFrame输出，方便下游处理")
    print()


if __name__ == "__main__":
    main()


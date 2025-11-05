"""DataCoder 节点使用示例

演示如何使用 DataCoder 节点进行智能数据处理
"""

import pandas as pd
from deepeye.nodes.datacoder import DataCoderNode
from deepeye.nodes.io import NodeInput, NodeStatus


def example_basic_filter():
    """示例1: 基本数据过滤"""
    print("\n" + "="*60)
    print("示例1: 基本数据过滤")
    print("="*60)
    
    # 创建测试数据
    df = pd.DataFrame({
        'name': ['Alice', 'Bob', 'Charlie', 'David', 'Eve'],
        'age': [25, 30, 35, 40, 45],
        'salary': [50000, 60000, 70000, 80000, 90000],
        'department': ['IT', 'HR', 'IT', 'Finance', 'IT']
    })
    
    print("\n原始数据:")
    print(df)
    
    # 创建 DataCoder 节点
    node = DataCoderNode(
        node_id="filter_node",
        config={
            "verbose": True  # API Key 从环境变量读取
        }
    )
    
    # 准备输入
    inputs = {
        "data": NodeInput(data=df),
        "task": NodeInput(data="过滤出年龄大于30岁的员工，并按薪水降序排列")
    }
    
    # 执行节点
    outputs = node.run(inputs)
    result = outputs["result"]
    
    # 检查结果
    if result.status == NodeStatus.SUCCESS:
        print("\n✅ 执行成功！")
        print(f"\n处理后的数据:")
        print(result.data["dataframe"])
        print(f"\n重试次数: {result.metrics.get('retries', 0)}")
        print(f"生成的代码:\n{result.metadata.get('code', 'N/A')}")
    else:
        print(f"\n❌ 执行失败: {result.error}")
    
    # 清理资源
    node.cleanup()


def example_statistics():
    """示例2: 统计分析"""
    print("\n" + "="*60)
    print("示例2: 统计分析")
    print("="*60)
    
    # 创建测试数据
    df = pd.DataFrame({
        'category': ['A', 'B', 'A', 'B', 'A', 'B'],
        'value': [10, 20, 30, 40, 50, 60]
    })
    
    print("\n原始数据:")
    print(df)
    
    # 创建节点
    node = DataCoderNode(
        node_id="stats_node",
        config={"verbose": False}
    )
    
    # 执行统计任务
    inputs = {
        "data": NodeInput(data=df),
        "task": NodeInput(data="按 category 分组，计算 value 的平均值、最大值和最小值")
    }
    
    outputs = node.run(inputs)
    result = outputs["result"]
    
    if result.status == NodeStatus.SUCCESS:
        print("\n✅ 执行成功！")
        print(f"\n统计结果:")
        print(result.data["dataframe"])
        print(f"\n生成的代码:\n{result.metadata.get('code', 'N/A')}")
    else:
        print(f"\n❌ 执行失败: {result.error}")
    
    node.cleanup()


def example_data_transformation():
    """示例3: 数据转换"""
    print("\n" + "="*60)
    print("示例3: 数据转换")
    print("="*60)
    
    # 创建测试数据
    df = pd.DataFrame({
        'date': ['2024-01-01', '2024-01-02', '2024-01-03'],
        'temperature': [15.5, 18.2, 16.8],
        'humidity': [65, 70, 68]
    })
    
    print("\n原始数据:")
    print(df)
    
    # 创建节点
    node = DataCoderNode(
        node_id="transform_node",
        config={"verbose": False}
    )
    
    # 执行转换任务
    inputs = {
        "data": NodeInput(data=df),
        "task": NodeInput(data="将 date 列转换为日期类型，添加一个新列 comfort_index，计算为 (100 - abs(temperature - 20) * 2 - abs(humidity - 60) * 0.5)")
    }
    
    outputs = node.run(inputs)
    result = outputs["result"]
    
    if result.status == NodeStatus.SUCCESS:
        print("\n✅ 执行成功！")
        print(f"\n转换后的数据:")
        print(result.data["dataframe"])
        print(f"\n数据类型:")
        print(result.data["dataframe"].dtypes)
        print(f"\n生成的代码:\n{result.metadata.get('code', 'N/A')}")
    else:
        print(f"\n❌ 执行失败: {result.error}")
    
    node.cleanup()


def example_machine_learning():
    """示例4: 机器学习预测"""
    print("\n" + "="*60)
    print("示例4: 机器学习预测")
    print("="*60)
    
    # 创建测试数据
    df = pd.DataFrame({
        'study_hours': [1, 2, 3, 4, 5, 6, 7, 8],
        'practice_tests': [2, 3, 4, 5, 6, 7, 8, 9],
        'score': [50, 55, 60, 68, 75, 82, 88, 95]
    })
    
    print("\n原始数据:")
    print(df)
    
    # 创建节点
    node = DataCoderNode(
        node_id="ml_node",
        config={
            "verbose": False,
            "max_retries": 5  # ML 任务可能需要更多重试
        }
    )
    
    # 执行预测任务
    inputs = {
        "data": NodeInput(data=df),
        "task": NodeInput(data="使用线性回归模型，以 study_hours 和 practice_tests 作为特征预测 score，并添加预测值列 predicted_score")
    }
    
    outputs = node.run(inputs)
    result = outputs["result"]
    
    if result.status == NodeStatus.SUCCESS:
        print("\n✅ 执行成功！")
        print(f"\n预测结果:")
        print(result.data["dataframe"])
        print(f"\n重试次数: {result.metrics.get('retries', 0)}")
        print(f"\n生成的代码:\n{result.metadata.get('code', 'N/A')}")
    else:
        print(f"\n❌ 执行失败: {result.error}")
        print(f"重试次数: {result.metrics.get('retries', 0)}")
    
    node.cleanup()


def example_with_custom_llm():
    """示例5: 使用自定义 LLM 配置"""
    print("\n" + "="*60)
    print("示例5: 使用自定义 LLM 配置")
    print("="*60)
    
    # 创建测试数据
    df = pd.DataFrame({
        'product': ['A', 'B', 'C', 'D'],
        'price': [100, 200, 150, 300],
        'sales': [50, 30, 40, 20]
    })
    
    print("\n原始数据:")
    print(df)
    
    # 使用自定义 LLM 配置创建节点
    node = DataCoderNode(
        node_id="custom_llm_node",
        config={
            "api_key": "your-api-key-here",  # 或使用环境变量
            "base_url": "https://api.openai.com/v1",
            "model": "gpt-4",  # 使用更强大的模型
            "temperature": 0.1,  # 低温度以获得更确定的代码
            "max_retries": 3,
            "verbose": False
        }
    )
    
    # 执行复杂任务
    inputs = {
        "data": NodeInput(data=df),
        "task": NodeInput(data="计算每个产品的收入（price * sales），并添加收入占比列（revenue_ratio）")
    }
    
    outputs = node.run(inputs)
    result = outputs["result"]
    
    if result.status == NodeStatus.SUCCESS:
        print("\n✅ 执行成功！")
        print(f"\n结果:")
        print(result.data["dataframe"])
        print(f"\n生成的代码:\n{result.metadata.get('code', 'N/A')}")
    else:
        print(f"\n❌ 执行失败: {result.error}")
    
    node.cleanup()


def example_error_handling():
    """示例6: 错误处理和重试机制"""
    print("\n" + "="*60)
    print("示例6: 错误处理和重试机制")
    print("="*60)
    
    # 创建测试数据
    df = pd.DataFrame({
        'x': [1, 2, 3, 4, 5],
        'y': [2, 4, 6, 8, 10]
    })
    
    print("\n原始数据:")
    print(df)
    
    # 创建节点，启用详细日志以观察重试过程
    node = DataCoderNode(
        node_id="error_demo_node",
        config={
            "verbose": True,  # 启用详细日志
            "max_retries": 3
        }
    )
    
    # 使用一个可能导致错误的复杂任务
    inputs = {
        "data": NodeInput(data=df),
        "task": NodeInput(data="使用多项式回归（2次）拟合数据，并添加预测列")
    }
    
    outputs = node.run(inputs)
    result = outputs["result"]
    
    if result.status == NodeStatus.SUCCESS:
        print("\n✅ 最终执行成功！")
        print(f"\n结果:")
        print(result.data["dataframe"])
        print(f"\n总重试次数: {result.metrics.get('retries', 0)}")
        
        # 打印执行日志
        print("\n执行历史:")
        for i, log in enumerate(result.metadata.get('execution_log', []), 1):
            print(f"\n第 {i} 次尝试:")
            print(f"  成功: {log['success']}")
            if log['error']:
                print(f"  错误: {log['error']}")
    else:
        print(f"\n❌ 执行失败: {result.error}")
        print(f"总重试次数: {result.metrics.get('retries', 0)}")
    
    node.cleanup()


def main():
    """运行所有示例"""
    print("\n" + "="*60)
    print("DataCoder 节点使用示例")
    print("="*60)
    print("\n请确保已设置环境变量 OPENAI_API_KEY")
    print("或在代码中提供 api_key 参数\n")
    
    try:
        # 运行基本示例
        example_basic_filter()
        
        # 运行统计示例
        example_statistics()
        
        # 运行数据转换示例
        example_data_transformation()
        
        # 运行机器学习示例（可能需要更长时间）
        # example_machine_learning()
        
        # 运行错误处理示例
        # example_error_handling()
        
        print("\n" + "="*60)
        print("所有示例执行完成！")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ 示例执行出错: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()


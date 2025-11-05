"""DataPlot 节点使用示例

展示如何使用 DataPlotNode 进行智能数据可视化
"""

import os
import pandas as pd
from pathlib import Path

from deepeye.nodes.dataplot import DataPlotNode
from deepeye.nodes.io import NodeInput


def example_1_simple_line_chart():
    """示例 1: 简单折线图"""
    print("\n" + "="*60)
    print("示例 1: 简单折线图")
    print("="*60)
    
    # 准备数据
    df = pd.DataFrame({
        'month': ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
        'sales': [100, 150, 120, 180, 200, 190],
        'costs': [80, 100, 90, 120, 130, 125]
    })
    
    print("\n输入数据:")
    print(df)
    
    # 创建节点
    node = DataPlotNode(
        node_id="plot1",
        config={
            "api_key": os.getenv("OPENAI_API_KEY"),
            "base_url": os.getenv("OPENAI_BASE_URL"),
            "model": "gpt-4o",
            "verbose": True
        }
    )
    
    # 执行可视化
    outputs = node.run({
        "data": NodeInput(data={"dataframe": df}),
        "task": NodeInput(data={
            "description": "绘制月度销售额的折线图，标题为'Monthly Sales Trend'"
        })
    })
    
    # 处理结果
    result = outputs["images"]
    if result.data:
        print(f"\n✅ 成功生成 {len(result.data)} 个图片:")
        for i, image in enumerate(result.data):
            print(f"\n图片 {i+1}:")
            print(f"  文件名: {image['filename']}")
            print(f"  描述: {image['description']}")
            print(f"  格式: {image['format']}")
            print(f"  大小: {image['file_size']} 字节")
            
            # 保存图片
            output_path = Path(f"output_{image['filename']}")
            with open(output_path, "wb") as f:
                f.write(image["data"])
            print(f"  已保存到: {output_path.absolute()}")
    else:
        print(f"\n❌ 生成失败: {result.metadata.get('error')}")


def example_2_multiple_charts():
    """示例 2: 多个图表"""
    print("\n" + "="*60)
    print("示例 2: 一次生成多个图表")
    print("="*60)
    
    # 准备数据
    df = pd.DataFrame({
        'product': ['A', 'B', 'C', 'D', 'E'],
        'sales': [100, 150, 120, 180, 200],
        'profit': [20, 35, 25, 45, 50],
        'market_share': [15, 22, 18, 25, 20]
    })
    
    print("\n输入数据:")
    print(df)
    
    # 创建节点
    node = DataPlotNode(
        node_id="plot2",
        config={
            "api_key": os.getenv("OPENAI_API_KEY"),
            "base_url": os.getenv("OPENAI_BASE_URL"),
            "model": "gpt-4o",
            "verbose": True
        }
    )
    
    # 执行可视化
    outputs = node.run({
        "data": NodeInput(data={"dataframe": df}),
        "task": NodeInput(data={
            "description": """
            创建三个图表：
            1. 产品销售额的柱状图
            2. 产品利润的饼图
            3. 市场份额的水平条形图
            """
        })
    })
    
    # 处理结果
    result = outputs["images"]
    if result.data:
        print(f"\n✅ 成功生成 {len(result.data)} 个图片")
        for i, image in enumerate(result.data):
            output_path = Path(f"multi_{i+1}_{image['filename']}")
            with open(output_path, "wb") as f:
                f.write(image["data"])
            print(f"  {i+1}. {image['description']} -> {output_path}")


def example_3_multi_dataframe():
    """示例 3: 多 DataFrame 可视化"""
    print("\n" + "="*60)
    print("示例 3: 多 DataFrame 可视化")
    print("="*60)
    
    # 准备多个 DataFrame
    df1 = pd.DataFrame({
        'year': [2019, 2020, 2021, 2022, 2023],
        'revenue': [100, 120, 150, 180, 200]
    })
    
    df2 = pd.DataFrame({
        'department': ['Sales', 'Marketing', 'R&D', 'Operations'],
        'headcount': [50, 30, 40, 60],
        'budget': [500, 300, 600, 400]
    })
    
    print("\nDataFrame 0 (df0):")
    print(df1)
    print("\nDataFrame 1 (df1):")
    print(df2)
    
    # 创建节点
    node = DataPlotNode(
        node_id="plot3",
        config={
            "api_key": os.getenv("OPENAI_API_KEY"),
            "base_url": os.getenv("OPENAI_BASE_URL"),
            "model": "gpt-4o",
            "verbose": True
        }
    )
    
    # 执行可视化
    outputs = node.run({
        "data": NodeInput(data={"dataframe_list": [df1, df2]}),
        "task": NodeInput(data={
            "description": """
            创建一个包含两个子图的图表：
            - 左边：df0 的年度收入折线图
            - 右边：df1 的各部门人数柱状图
            使用 subplot 布局
            """
        })
    })
    
    # 处理结果
    result = outputs["images"]
    if result.data:
        print(f"\n✅ 成功生成 {len(result.data)} 个图片")
        for image in result.data:
            output_path = Path(f"multi_df_{image['filename']}")
            with open(output_path, "wb") as f:
                f.write(image["data"])
            print(f"  {image['description']} -> {output_path}")


def example_4_advanced_visualization():
    """示例 4: 高级可视化（热力图、散点图等）"""
    print("\n" + "="*60)
    print("示例 4: 高级可视化")
    print("="*60)
    
    # 准备数据
    import numpy as np
    
    df = pd.DataFrame({
        'age': np.random.randint(20, 60, 100),
        'income': np.random.randint(30000, 150000, 100),
        'satisfaction': np.random.randint(1, 11, 100),
        'category': np.random.choice(['A', 'B', 'C'], 100)
    })
    
    print("\n输入数据（前 10 行）:")
    print(df.head(10))
    
    # 创建节点
    node = DataPlotNode(
        node_id="plot4",
        config={
            "api_key": os.getenv("OPENAI_API_KEY"),
            "base_url": os.getenv("OPENAI_BASE_URL"),
            "model": "gpt-4o",
            "verbose": True
        }
    )
    
    # 执行可视化
    outputs = node.run({
        "data": NodeInput(data={"dataframe": df}),
        "task": NodeInput(data={
            "description": """
            创建一个散点图，显示年龄和收入的关系：
            - X轴：年龄
            - Y轴：收入
            - 颜色：按类别（category）分组
            - 大小：按满意度（satisfaction）调整点的大小
            添加趋势线和图例
            """
        })
    })
    
    # 处理结果
    result = outputs["images"]
    if result.data:
        print(f"\n✅ 成功生成 {len(result.data)} 个图片")
        for image in result.data:
            output_path = Path(f"advanced_{image['filename']}")
            with open(output_path, "wb") as f:
                f.write(image["data"])
            print(f"  {image['description']} -> {output_path}")


def main():
    """运行所有示例"""
    # 检查 API Key
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ 错误: 请设置 OPENAI_API_KEY 环境变量")
        print("   export OPENAI_API_KEY='your-api-key'")
        return
    
    # 可选：显示配置信息
    base_url = os.getenv("OPENAI_BASE_URL")
    if base_url:
        print(f"ℹ️  使用自定义 Base URL: {base_url}")
    else:
        print("ℹ️  使用默认 OpenAI Base URL")
    
    print("\n" + "🎨"*30)
    print("DataPlot 节点使用示例")
    print("🎨"*30)
    
    try:
        # 运行示例
        # example_1_simple_line_chart()
        
        # 可选：取消注释运行其他示例
        # example_2_multiple_charts()
        # example_3_multi_dataframe()
        example_4_advanced_visualization()
        
        print("\n" + "="*60)
        print("✅ 所有示例运行完成！")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ 运行出错: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()


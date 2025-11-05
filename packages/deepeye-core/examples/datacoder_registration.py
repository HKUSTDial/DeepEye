"""DataCoder 节点注册示例

演示如何将 DataCoder 节点注册到节点注册表
"""

from deepeye.nodes import get_registry, register_node
from deepeye.nodes.datacoder import DataCoderNode
from deepeye.nodes.io import NodeInput, NodeStatus
import pandas as pd


def example_register_and_use():
    """注册并使用 DataCoder 节点"""
    print("\n" + "="*60)
    print("DataCoder 节点注册示例")
    print("="*60)
    
    # 1. 注册节点到全局注册表
    print("\n步骤 1: 注册节点")
    register_node(DataCoderNode)
    print(f"✓ 已注册节点: DataCoder")
    
    # 2. 查看注册表
    print("\n步骤 2: 查看注册表")
    registry = get_registry()
    node_types = registry.list_node_types()
    print(f"已注册的节点类型: {node_types}")
    
    # 3. 从注册表创建节点实例
    print("\n步骤 3: 从注册表创建节点")
    node = registry.create_node(
        node_type="DataCoder",
        node_id="coder1",
        config={
            "verbose": False
        }
    )
    print(f"✓ 创建节点: {node}")
    
    # 4. 使用节点
    print("\n步骤 4: 使用节点处理数据")
    df = pd.DataFrame({
        'name': ['Alice', 'Bob', 'Charlie', 'David'],
        'age': [25, 30, 35, 40],
        'salary': [50000, 60000, 70000, 80000]
    })
    
    print("原始数据:")
    print(df)
    
    inputs = {
        "data": NodeInput(data=df),
        "task": NodeInput(data="过滤出年龄大于30的员工")
    }
    
    outputs = node.run(inputs)
    result = outputs["result"]
    
    if result.status == NodeStatus.SUCCESS:
        print("\n✅ 执行成功！")
        print("\n处理后的数据:")
        print(result.data)
        print(f"\n生成的代码:")
        print(result.metadata.get('code'))
    else:
        print(f"\n❌ 执行失败: {result.error}")
    
    # 5. 清理
    node.cleanup()
    print("\n✓ 资源已清理")


def example_get_node_info():
    """获取节点信息"""
    print("\n" + "="*60)
    print("获取节点信息")
    print("="*60)
    
    # 确保节点已注册
    register_node(DataCoderNode)
    
    # 获取节点信息
    registry = get_registry()
    info = registry.get_node_info("DataCoder")
    
    print(f"\n节点类型: {info['node_type']}")
    print(f"类名: {info['class_name']}")
    
    print(f"\n元数据:")
    metadata = info['metadata']
    print(f"  名称: {metadata['name']}")
    print(f"  显示名称: {metadata['display_name']}")
    print(f"  描述: {metadata['description']}")
    print(f"  类别: {metadata['category']}")
    print(f"  标签: {metadata['tags']}")
    print(f"  版本: {metadata['version']}")
    
    print(f"\n输入端口:")
    for port in info['input_ports']:
        print(f"  - {port['name']} ({port['label']})")
    
    print(f"\n输出端口:")
    for port in info['output_ports']:
        print(f"  - {port['name']} ({port['label']})")


def example_multiple_nodes():
    """注册和使用多个节点"""
    print("\n" + "="*60)
    print("多节点场景")
    print("="*60)
    
    # 注册 DataCoder 节点
    register_node(DataCoderNode)
    
    # 创建多个节点实例
    registry = get_registry()
    
    node1 = registry.create_node(
        "DataCoder",
        node_id="filter_node",
        config={"verbose": False}
    )
    
    node2 = registry.create_node(
        "DataCoder",
        node_id="stats_node",
        config={"verbose": False}
    )
    
    print(f"创建了 2 个节点:")
    print(f"  1. {node1}")
    print(f"  2. {node2}")
    
    # 使用第一个节点进行过滤
    df = pd.DataFrame({
        'category': ['A', 'B', 'A', 'B', 'A'],
        'value': [10, 20, 30, 40, 50]
    })
    
    print("\n原始数据:")
    print(df)
    
    # 节点 1: 过滤
    print("\n节点 1: 过滤类别 A")
    outputs1 = node1.run({
        "data": NodeInput(data=df),
        "task": NodeInput(data="过滤出 category 为 'A' 的记录")
    })
    
    if outputs1["result"].status == NodeStatus.SUCCESS:
        filtered_df = outputs1["result"].data
        print("过滤后:")
        print(filtered_df)
        
        # 节点 2: 统计
        print("\n节点 2: 计算统计信息")
        outputs2 = node2.run({
            "data": NodeInput(data=filtered_df),
            "task": NodeInput(data="计算 value 的平均值、最大值和最小值")
        })
        
        if outputs2["result"].status == NodeStatus.SUCCESS:
            stats_df = outputs2["result"].data
            print("统计结果:")
            print(stats_df)
        else:
            print(f"节点 2 失败: {outputs2['result'].error}")
    else:
        print(f"节点 1 失败: {outputs1['result'].error}")
    
    # 清理
    node1.cleanup()
    node2.cleanup()


def main():
    """运行所有示例"""
    try:
        # 示例 1: 基本注册和使用
        example_register_and_use()
        
        # 示例 2: 获取节点信息
        example_get_node_info()
        
        # 示例 3: 多节点场景
        # example_multiple_nodes()
        
        print("\n" + "="*60)
        print("所有示例执行完成！")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ 示例执行出错: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()


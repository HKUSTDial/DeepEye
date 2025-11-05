"""工作流系统基础使用示例

展示如何创建和使用工作流。
"""

from deepeye.workflow import Workflow
from deepeye.nodes import BaseNode, NodeOutput, NodeMetadata, NodeInputPort
from deepeye.nodes.io import NodeOutputPort


# ========== 定义示例节点 ==========

class DataSourceNode(BaseNode):
    """数据源节点：模拟从数据源读取数据"""
    
    node_type = "DataSource"
    
    def __init__(self, node_id=None, config=None):
        super().__init__(node_id, config)
        self.metadata = NodeMetadata(
            name="DataSource",
            display_name="数据源",
            description="从数据源读取数据"
        )
        
        # 数据源节点没有输入端口（是工作流的起点）
        self.input_ports = []
        
        # 有一个输出端口
        self.output_ports = [
            NodeOutputPort(name="data", label="数据输出")
        ]
    
    def execute(self, inputs):
        # 模拟读取数据
        data = {
            "students": [
                {"name": "张三", "age": 20, "score": 85},
                {"name": "李四", "age": 21, "score": 90},
                {"name": "王五", "age": 22, "score": 78},
            ]
        }
        
        return {
            "data": NodeOutput(
                data=data,
                metadata={"rows": len(data["students"])}
            )
        }


class FilterNode(BaseNode):
    """过滤节点：根据条件过滤数据"""
    
    node_type = "Filter"
    
    def __init__(self, node_id=None, config=None):
        super().__init__(node_id, config)
        self.metadata = NodeMetadata(
            name="Filter",
            display_name="过滤",
            description="根据条件过滤数据"
        )
        
        self.input_ports = [
            NodeInputPort(name="data", label="输入数据", required=True)
        ]
        
        self.output_ports = [
            NodeOutputPort(name="filtered", label="过滤后的数据")
        ]
    
    def execute(self, inputs):
        input_data = self.get_single_input(inputs)
        students = input_data.get("students", [])
        
        # 过滤出分数大于80的学生
        filtered = [s for s in students if s.get("score", 0) > 80]
        
        return {
            "filtered": NodeOutput(
                data={"students": filtered},
                metadata={"filtered_count": len(filtered)}
            )
        }


class TransformNode(BaseNode):
    """转换节点：转换数据格式"""
    
    node_type = "Transform"
    
    def __init__(self, node_id=None, config=None):
        super().__init__(node_id, config)
        self.metadata = NodeMetadata(
            name="Transform",
            display_name="转换",
            description="转换数据格式"
        )
        
        self.input_ports = [
            NodeInputPort(name="data", label="输入数据", required=True)
        ]
        
        self.output_ports = [
            NodeOutputPort(name="transformed", label="转换后的数据")
        ]
    
    def execute(self, inputs):
        input_data = self.get_single_input(inputs)
        students = input_data.get("students", [])
        
        # 转换为报告格式
        report = {
            "total": len(students),
            "names": [s["name"] for s in students],
            "avg_score": sum(s["score"] for s in students) / len(students) if students else 0
        }
        
        return {
            "transformed": NodeOutput(
                data=report,
                metadata={"report_type": "summary"}
            )
        }


# ========== 示例 1: 使用 Workflow 类直接创建 ==========

def example_1_direct_workflow():
    """示例 1: 直接使用 Workflow 类创建工作流"""
    print("=" * 60)
    print("示例 1: 直接使用 Workflow 类创建工作流")
    print("=" * 60)
    
    # 创建工作流
    workflow = Workflow(
        name="数据处理工作流",
        description="读取数据、过滤、转换"
    )
    
    # 添加节点
    workflow.add_node("source", DataSourceNode())
    workflow.add_node("filter", FilterNode())
    workflow.add_node("transform", TransformNode())
    
    # 连接节点
    workflow.connect("source", "filter", from_port="data", to_port="data")
    workflow.connect("filter", "transform", from_port="filtered", to_port="data")
    
    # 验证工作流
    print(f"工作流: {workflow.metadata.name}")
    print(f"节点数: {len(workflow.list_nodes())}")
    print(f"连接数: {len(workflow.get_connections())}")
    print(f"是否有效: {workflow.is_valid()}")
    
    # 获取执行顺序
    order = workflow.get_execution_order()
    print(f"执行顺序: {' -> '.join(order)}")
    
    # 获取执行层级（可并行执行的节点分组）
    layers = workflow.get_execution_layers()
    print(f"执行层级:")
    for i, layer in enumerate(layers):
        print(f"  第{i+1}层: {', '.join(layer)}")
    
    print()


# ========== 示例 2: 使用链式调用构建 ==========

def example_2_chaining():
    """示例 2: 使用链式调用构建工作流"""
    print("=" * 60)
    print("示例 2: 使用链式调用构建工作流")
    print("=" * 60)
    
    # 使用Workflow，支持链式调用
    workflow = (Workflow(name="链式调用示例", description="使用链式API")
                .add_node("source", DataSourceNode())
                .add_node("filter", FilterNode())
                .add_node("transform", TransformNode())
                .connect("source", "filter")
                .connect("filter", "transform"))
    
    # 获取验证报告
    report = workflow.get_validation_report()
    print(f"验证状态: {'✅ 通过' if report.is_valid else '❌ 失败'}")
    
    print(f"节点数: {workflow.graph.node_count()}")
    print(f"边数: {workflow.graph.edge_count()}")
    print(f"是否DAG: {workflow.graph.is_dag()}")
    print(f"工作流名称: {workflow.metadata.name}")
    
    print()


# ========== 示例 3: 复杂工作流（分支和合并）==========

class MergeNode(BaseNode):
    """合并节点：合并多个输入"""
    
    node_type = "Merge"
    
    def __init__(self, node_id=None, config=None):
        super().__init__(node_id, config)
        self.metadata = NodeMetadata(
            name="Merge",
            display_name="合并",
            description="合并多个输入"
        )
        
        # 两个输入端口
        self.input_ports = [
            NodeInputPort(name="input1", label="输入1", required=True),
            NodeInputPort(name="input2", label="输入2", required=True),
        ]
        
        self.output_ports = [
            NodeOutputPort(name="merged", label="合并后的数据")
        ]
    
    def execute(self, inputs):
        data1 = inputs["input1"].get("students", [])
        data2 = inputs["input2"].get("students", [])
        
        # 合并两个列表
        merged = data1 + data2
        
        return {
            "merged": NodeOutput(
                data={"students": merged},
                metadata={"total": len(merged)}
            )
        }


def example_3_complex_workflow():
    """示例 3: 复杂工作流（分支和合并）"""
    print("=" * 60)
    print("示例 3: 复杂工作流（分支和合并）")
    print("=" * 60)
    
    workflow = Workflow(name="分支合并工作流")
    
    # 添加节点
    workflow.add_node("source", DataSourceNode())
    workflow.add_node("filter1", FilterNode())  # 分支1
    workflow.add_node("filter2", FilterNode())  # 分支2
    workflow.add_node("merge", MergeNode())
    workflow.add_node("transform", TransformNode())
    
    # 创建连接：source 分支到 filter1 和 filter2
    workflow.connect("source", "filter1")
    workflow.connect("source", "filter2")
    
    # filter1 和 filter2 合并到 merge
    workflow.connect("filter1", "merge", to_port="input1")
    workflow.connect("filter2", "merge", to_port="input2")
    
    # merge 到 transform
    workflow.connect("merge", "transform")
    
    print(f"节点数: {len(workflow.list_nodes())}")
    print(f"根节点: {workflow.get_root_nodes()}")
    print(f"叶子节点: {workflow.get_leaf_nodes()}")
    
    # 显示每个节点的依赖关系
    print("\n节点依赖关系:")
    for node_id in workflow.list_nodes():
        deps = workflow.get_node_dependencies(node_id)
        dependents = workflow.get_node_dependents(node_id)
        print(f"  {node_id}:")
        print(f"    依赖: {deps if deps else '无'}")
        print(f"    被依赖: {dependents if dependents else '无'}")
    
    # 执行层级（可并行执行的节点）
    layers = workflow.get_execution_layers()
    print("\n可并行执行的层级:")
    for i, layer in enumerate(layers):
        print(f"  层{i+1}: {', '.join(layer)}")
    
    print()


# ========== 示例 4: 工作流序列化和持久化 ==========

def example_4_serialization():
    """示例 4: 工作流序列化和持久化"""
    print("=" * 60)
    print("示例 4: 工作流序列化和持久化")
    print("=" * 60)
    
    # 创建工作流
    workflow = Workflow(name="可序列化工作流", description="演示序列化功能")
    workflow.add_node("source", DataSourceNode())
    workflow.add_node("filter", FilterNode())
    workflow.connect("source", "filter")
    
    # 导出为字典
    data = workflow.to_dict()
    print("导出为字典:")
    print(f"  ID: {data['workflow_id'][:8]}...")
    print(f"  名称: {data['metadata']['name']}")
    print(f"  节点数: {len(data['nodes'])}")
    print(f"  连接数: {len(data['graph']['edges'])}")
    
    # 导出为JSON
    json_str = workflow.to_json()
    print(f"\nJSON长度: {len(json_str)} 字符")
    
    # 从字典恢复工作流
    loaded = Workflow.from_dict(data)
    print(f"\n从字典恢复:")
    print(f"  名称: {loaded.metadata.name}")
    print(f"  节点数: {loaded.graph.node_count()}")
    
    # 保存到文件（演示，不实际保存）
    # workflow.save("workflow.json")
    # loaded = Workflow.load("workflow.json")
    
    print()


# ========== 示例 5: 工作流验证错误处理 ==========

def example_5_validation_errors():
    """示例 5: 工作流验证错误处理"""
    print("=" * 60)
    print("示例 5: 工作流验证错误处理")
    print("=" * 60)
    
    # 创建一个有问题的工作流
    workflow = Workflow(name="有问题的工作流")
    
    # 添加一个有必需输入的根节点（这是错误的）
    workflow.add_node("filter", FilterNode())
    
    # 验证（不会抛出异常）
    is_valid = workflow.validate()
    print(f"验证结果: {'✅ 通过' if is_valid else '❌ 失败'}")
    
    # 获取详细的验证报告
    report = workflow.get_validation_report()
    print(f"\n验证报告:")
    print(f"  错误数: {len(report.errors)}")
    print(f"  警告数: {len(report.warnings)}")
    
    if report.errors:
        print("\n错误详情:")
        for error in report.errors:
            print(f"  - {error}")
    
    print()


def main():
    """运行所有示例"""
    print("\n")
    print("🚀 DeepEye 工作流系统使用示例")
    print("=" * 60)
    print()
    
    # 运行所有示例
    example_1_direct_workflow()
    example_2_chaining()
    example_3_complex_workflow()
    example_4_serialization()
    example_5_validation_errors()
    
    print("=" * 60)
    print("✅ 所有示例执行完成！")
    print()


if __name__ == "__main__":
    main()


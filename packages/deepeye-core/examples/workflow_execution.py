"""工作流执行完整示例

展示如何使用 WorkflowExecutor 执行完整的工作流。
"""

from deepeye import Workflow, WorkflowExecutor
from deepeye.nodes import BaseNode, NodeInput, NodeOutput, NodeInputPort, NodeOutputPort
from deepeye.runtime import ExecutionStatus


# ========== 定义示例节点 ==========

class DataSourceNode(BaseNode):
    """数据源节点 - 生成数据"""
    
    node_type = "DataSource"
    
    def __init__(self, node_id=None, data_size=10):
        super().__init__(node_id)
        self.data_size = data_size
        self.input_ports = []  # 无输入
        self.output_ports = [
            NodeOutputPort(name="data", label="数据输出")
        ]
    
    def execute(self, inputs):
        # 生成示例数据
        data = list(range(1, self.data_size + 1))
        
        return {"data": NodeOutput(
            data={"values": data},
            metadata={"count": len(data)}
        )}


class FilterNode(BaseNode):
    """过滤节点 - 过滤数据"""
    
    node_type = "Filter"
    
    def __init__(self, node_id=None, threshold=5):
        super().__init__(node_id)
        self.threshold = threshold
        self.input_ports = [
            NodeInputPort(name="data", label="输入数据", required=True)
        ]
        self.output_ports = [
            NodeOutputPort(name="filtered", label="过滤后数据")
        ]
    
    def execute(self, inputs):
        input_data = self.get_single_input(inputs)
        values = input_data.get("values", [])
        
        # 过滤数据
        filtered = [v for v in values if v > self.threshold]
        
        return {"filtered": NodeOutput(
            data={"values": filtered},
            metadata={"count": len(filtered), "threshold": self.threshold}
        )}


class TransformNode(BaseNode):
    """转换节点 - 转换数据"""
    
    node_type = "Transform"
    
    def __init__(self, node_id=None, operation="square"):
        super().__init__(node_id)
        self.operation = operation
        self.input_ports = [
            NodeInputPort(name="data", label="输入数据", required=True)
        ]
        self.output_ports = [
            NodeOutputPort(name="transformed", label="转换后数据")
        ]
    
    def execute(self, inputs):
        input_data = self.get_single_input(inputs)
        values = input_data.get("values", [])
        
        # 转换数据
        if self.operation == "square":
            transformed = [v ** 2 for v in values]
        elif self.operation == "double":
            transformed = [v * 2 for v in values]
        else:
            transformed = values
        
        return {"transformed": NodeOutput(
            data={"values": transformed},
            metadata={"operation": self.operation}
        )}


class AggregateNode(BaseNode):
    """聚合节点 - 聚合多个输入"""
    
    node_type = "Aggregate"
    
    def __init__(self, node_id=None):
        super().__init__(node_id)
        self.input_ports = [
            NodeInputPort(name="input1", label="输入1", required=True),
            NodeInputPort(name="input2", label="输入2", required=True),
        ]
        self.output_ports = [
            NodeOutputPort(name="result", label="聚合结果")
        ]
    
    def execute(self, inputs):
        values1 = inputs["input1"].get("values", [])
        values2 = inputs["input2"].get("values", [])
        
        # 计算统计信息
        all_values = values1 + values2
        
        result = {
            "sum": sum(all_values),
            "count": len(all_values),
            "avg": sum(all_values) / len(all_values) if all_values else 0,
            "min": min(all_values) if all_values else 0,
            "max": max(all_values) if all_values else 0,
        }
        
        return {"result": NodeOutput(
            data=result,
            metadata={"input_count": len(all_values)}
        )}


# ========== 示例 1: 简单线性工作流 ==========

def example_1_simple_linear():
    """示例 1: 简单线性工作流"""
    print("=" * 60)
    print("示例 1: 简单线性工作流")
    print("=" * 60)
    
    # 创建工作流: source -> filter -> transform
    workflow = Workflow(name="线性处理", workflow_id="linear")
    
    # 添加节点
    source = DataSourceNode(node_id="source", data_size=10)
    filter_node = FilterNode(node_id="filter", threshold=5)
    transform = TransformNode(node_id="transform", operation="square")
    
    workflow.add_node("source", source)
    workflow.add_node("filter", filter_node)
    workflow.add_node("transform", transform)
    
    # 添加连接
    workflow.add_connection("source", "filter", "data", "data")
    workflow.add_connection("filter", "transform", "filtered", "data")
    
    # 执行工作流
    executor = WorkflowExecutor(workflow)
    result = executor.execute()
    
    # 输出结果
    print(f"执行状态: {result.status.value}")
    print(f"耗时: {result.duration:.3f}秒")
    print()
    
    # 查看每个节点的输出
    print("节点执行结果:")
    for node_id in ["source", "filter", "transform"]:
        node_result = result.get_node_result(node_id)
        print(f"  {node_id}:")
        print(f"    状态: {node_result.status.value}")
        print(f"    耗时: {node_result.duration:.4f}秒")
        
        if node_result.outputs:
            for port_name, output in node_result.outputs.items():
                print(f"    输出 ({port_name}): {output.data}")
    
    print()
    
    # 统计信息
    stats = result.get_statistics()
    print(f"统计信息:")
    print(f"  总节点数: {stats['total_nodes']}")
    print(f"  成功: {stats['successful']}")
    print(f"  失败: {stats['failed']}")
    print(f"  成功率: {stats['success_rate']:.1%}")
    print()


# ========== 示例 2: 分支合并工作流 ==========

def example_2_branching_workflow():
    """示例 2: 分支合并工作流"""
    print("=" * 60)
    print("示例 2: 分支合并工作流")
    print("=" * 60)
    
    # 创建工作流: source -> (filter1, filter2) -> aggregate
    workflow = Workflow(name="分支处理", workflow_id="branching")
    
    # 添加节点
    source = DataSourceNode(node_id="source", data_size=20)
    filter1 = FilterNode(node_id="filter1", threshold=10)
    filter2 = FilterNode(node_id="filter2", threshold=5)
    aggregate = AggregateNode(node_id="aggregate")
    
    workflow.add_node("source", source)
    workflow.add_node("filter1", filter1)
    workflow.add_node("filter2", filter2)
    workflow.add_node("aggregate", aggregate)
    
    # 添加连接 - 创建分支
    workflow.add_connection("source", "filter1", "data", "data")
    workflow.add_connection("source", "filter2", "data", "data")
    workflow.add_connection("filter1", "aggregate", "filtered", "input1")
    workflow.add_connection("filter2", "aggregate", "filtered", "input2")
    
    # 执行工作流
    executor = WorkflowExecutor(workflow)
    result = executor.execute()
    
    # 输出结果
    print(f"执行状态: {result.status.value}")
    print(f"总耗时: {result.duration:.3f}秒")
    print()
    
    # 查看执行层级
    layers = executor.get_execution_layers()
    print("执行层级（可并行）:")
    for i, layer in enumerate(layers, 1):
        print(f"  层 {i}: {', '.join(layer)}")
    print()
    
    # 查看最终聚合结果
    aggregate_result = result.get_node_result("aggregate")
    if aggregate_result.status == ExecutionStatus.SUCCESS:
        agg_data = aggregate_result.outputs["result"].data
        print("聚合结果:")
        print(f"  总和: {agg_data['sum']}")
        print(f"  数量: {agg_data['count']}")
        print(f"  平均: {agg_data['avg']:.2f}")
        print(f"  最小值: {agg_data['min']}")
        print(f"  最大值: {agg_data['max']}")
    print()


# ========== 示例 3: 复杂多层工作流 ==========

def example_3_complex_workflow():
    """示例 3: 复杂多层工作流"""
    print("=" * 60)
    print("示例 3: 复杂多层工作流")
    print("=" * 60)
    
    # 创建复杂工作流
    workflow = Workflow(name="复杂处理流程", workflow_id="complex")
    
    # 第一层：数据源
    s1 = DataSourceNode(node_id="source1", data_size=10)
    s2 = DataSourceNode(node_id="source2", data_size=15)
    
    # 第二层：过滤
    f1 = FilterNode(node_id="filter1", threshold=3)
    f2 = FilterNode(node_id="filter2", threshold=8)
    
    # 第三层：转换
    t1 = TransformNode(node_id="transform1", operation="square")
    t2 = TransformNode(node_id="transform2", operation="double")
    
    # 第四层：聚合
    agg = AggregateNode(node_id="final_aggregate")
    
    # 添加所有节点
    for node in [s1, s2, f1, f2, t1, t2, agg]:
        workflow.add_node(node.node_id, node)
    
    # 添加连接
    workflow.add_connection("source1", "filter1", "data", "data")
    workflow.add_connection("source2", "filter2", "data", "data")
    workflow.add_connection("filter1", "transform1", "filtered", "data")
    workflow.add_connection("filter2", "transform2", "filtered", "data")
    workflow.add_connection("transform1", "final_aggregate", "transformed", "input1")
    workflow.add_connection("transform2", "final_aggregate", "transformed", "input2")
    
    # 验证工作流
    print("验证工作流...")
    is_valid = workflow.validate()
    if is_valid:
        print("✅ 工作流验证通过")
    else:
        print("❌ 工作流验证失败")
        return
    print()
    
    # 执行工作流
    print("执行工作流...")
    executor = WorkflowExecutor(workflow)
    result = executor.execute()
    
    # 输出结果
    print(f"执行状态: {result.status.value}")
    print(f"总耗时: {result.duration:.3f}秒")
    print()
    
    # 查看执行层级
    layers = executor.get_execution_layers()
    print(f"工作流分为 {len(layers)} 个执行层级:")
    for i, layer in enumerate(layers, 1):
        print(f"  层 {i}: {', '.join(layer)}")
    print()
    
    # 详细的节点执行信息
    print("节点执行详情:")
    print(f"{'节点ID':<20} {'状态':<10} {'耗时(ms)':<12}")
    print("-" * 42)
    
    for node_id in result.node_results.keys():
        node_result = result.get_node_result(node_id)
        duration_ms = node_result.duration * 1000 if node_result.duration else 0
        print(f"{node_id:<20} {node_result.status.value:<10} {duration_ms:>10.2f}")
    print()
    
    # 统计信息
    stats = result.get_statistics()
    print("统计汇总:")
    print(f"  总节点数: {stats['total_nodes']}")
    print(f"  成功: {stats['successful']}")
    print(f"  失败: {stats['failed']}")
    print(f"  跳过: {stats['skipped']}")
    print(f"  成功率: {stats['success_rate']:.1%}")
    print(f"  平均节点耗时: {stats['avg_node_duration']:.4f}秒")
    print()


# ========== 示例 4: 错误处理 ==========

def example_4_error_handling():
    """示例 4: 错误处理示例"""
    print("=" * 60)
    print("示例 4: 错误处理")
    print("=" * 60)
    
    # 创建一个会失败的节点
    class FailingNode(BaseNode):
        node_type = "Failing"
        
        def __init__(self, node_id=None):
            super().__init__(node_id)
            self.input_ports = [NodeInputPort(name="data", label="数据", required=True)]
            self.output_ports = [NodeOutputPort(name="output", label="输出")]
        
        def execute(self, inputs):
            raise ValueError("这个节点故意失败以演示错误处理")
    
    # 创建工作流: source -> failing -> transform
    workflow = Workflow(name="错误处理", workflow_id="error_handling")
    
    source = DataSourceNode(node_id="source", data_size=5)
    failing = FailingNode(node_id="failing")
    transform = TransformNode(node_id="transform", operation="square")
    
    workflow.add_node("source", source)
    workflow.add_node("failing", failing)
    workflow.add_node("transform", transform)
    
    workflow.add_connection("source", "failing", "data", "data")
    workflow.add_connection("failing", "transform", "output", "data")
    
    # 执行工作流（fail_fast=True）
    print("执行模式: 快速失败 (fail_fast=True)")
    executor = WorkflowExecutor(workflow, fail_fast=True)
    result = executor.execute()
    
    print(f"执行状态: {result.status.value}")
    print()
    
    # 查看各节点状态
    print("节点状态:")
    for node_id in ["source", "failing", "transform"]:
        node_result = result.get_node_result(node_id)
        print(f"  {node_id}: {node_result.status.value}")
        if node_result.error:
            print(f"    错误: {node_result.error}")
    print()
    
    # 统计
    print("执行统计:")
    print(f"  成功节点: {', '.join(result.get_successful_nodes())}")
    print(f"  失败节点: {', '.join(result.get_failed_nodes())}")
    print(f"  跳过节点: {', '.join(result.get_skipped_nodes())}")
    print()


# ========== 主函数 ==========

def main():
    """运行所有示例"""
    print("\n")
    print("🚀 DeepEye 工作流执行系统示例")
    print("=" * 60)
    print()
    
    # 运行所有示例
    example_1_simple_linear()
    example_2_branching_workflow()
    example_3_complex_workflow()
    example_4_error_handling()
    
    print("=" * 60)
    print("✅ 所有示例执行完成！")
    print()


if __name__ == "__main__":
    main()


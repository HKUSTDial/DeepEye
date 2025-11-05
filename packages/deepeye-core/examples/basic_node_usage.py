"""节点系统基础使用示例

展示如何创建和使用节点。
"""

from deepeye.nodes import (
    BaseNode,
    NodeInput,
    NodeOutput,
    NodeMetadata,
    NodeInputPort,
    NodeOutputPort,
    NodeInputSchema,
    NodeOutputSchema,
    register_node,
    get_registry,
)


# ========== 示例 1: 创建简单的自定义节点 ==========

class GreetingNode(BaseNode):
    """问候节点：给输入的名字添加问候语"""
    
    node_type = "Greeting"
    
    def __init__(self, node_id=None, config=None):
        super().__init__(node_id, config)
        
        # 设置节点元数据
        self.metadata = NodeMetadata(
            name="Greeting",
            display_name="问候节点",
            description="给输入的名字添加问候语",
            category="processing",
            tags=["string", "transform"]
        )
        
        # 定义输入端口
        self.input_ports = [
            NodeInputPort(
                name="input",
                label="输入名字",
                schemas=[
                    NodeInputSchema(
                        name="name",
                        type="string",
                        required=True,
                        description="要问候的名字"
                    )
                ]
            )
        ]
        
        # 定义输出端口
        self.output_ports = [
            NodeOutputPort(
                name="output",
                label="问候语",
                schemas=[
                    NodeOutputSchema(
                        name="greeting",
                        type="string",
                        description="生成的问候语"
                    )
                ]
            )
        ]
    
    def execute(self, inputs: dict) -> dict:
        """执行节点逻辑"""
        # 获取输入数据
        input_data = inputs.get("input", NodeInput())
        name = input_data.get("name", "朋友")
        greeting = f"你好，{name}！欢迎使用 DeepEye！"
        
        output = NodeOutput(data={"greeting": greeting})
        output.add_log(f"为 '{name}' 生成了问候语")
        output.set_metric("name_length", len(name))
        
        return {"output": output}


def example_1_basic_node():
    """示例 1: 基础节点使用"""
    print("=" * 60)
    print("示例 1: 基础节点使用")
    print("=" * 60)
    
    # 创建节点实例
    node = GreetingNode(node_id="greeting-001")
    
    # 打印节点信息
    print(f"节点类型: {node.node_type}")
    print(f"节点ID: {node.node_id}")
    print(f"节点描述: {node.metadata.description}")
    print()
    
    # 准备输入数据
    inputs = {"input": NodeInput(data={"name": "张三"})}
    
    # 执行节点
    outputs = node.run(inputs)
    output = outputs["output"]
    
    # 查看输出
    print(f"执行状态: {output.status.value}")
    print(f"输出数据: {output.data}")
    print(f"执行日志:")
    for log in output.logs:
        print(f"  - {log}")
    print(f"执行指标: {output.metrics}")
    print()


# ========== 示例 2: 节点注册和管理 ==========

@register_node
class AddNode(BaseNode):
    """加法节点：将两个数字相加"""
    
    node_type = "Add"
    
    def __init__(self, node_id=None, config=None):
        super().__init__(node_id, config)
        self.metadata = NodeMetadata(
            name="Add",
            display_name="加法节点",
            description="将两个数字相加"
        )
        from deepeye.nodes.io import NodeInputPort
        self.input_ports = [
            NodeInputPort(name="data", label="数据输入", required=True)
        ]
        self.output_ports = [
            NodeOutputPort(name="output", label="输出")
        ]
    
    def execute(self, inputs: dict) -> dict:
        input_data = self.get_single_input(inputs)
        a = input_data.get("a", 0)
        b = input_data.get("b", 0)
        result = a + b
        
        return self.create_single_output(
            data={"result": result},
            metadata={"operation": "addition"}
        )


def example_2_node_registry():
    """示例 2: 节点注册表"""
    print("=" * 60)
    print("示例 2: 节点注册表")
    print("=" * 60)
    
    # 获取全局注册表
    registry = get_registry()
    
    # 列出所有已注册的节点
    print(f"已注册的节点类型: {registry.list_node_types()}")
    print()
    
    # 通过注册表创建节点
    add_node = registry.create_node("Add")
    
    # 执行节点
    inputs = {"data": NodeInput(data={"a": 10, "b": 20})}
    outputs = add_node.run(inputs)
    output = outputs["output"]
    
    print(f"10 + 20 = {output.data['result']}")
    print(f"元数据: {output.metadata}")
    print()


# ========== 示例 3: 节点链式执行 ==========

class DoubleNode(BaseNode):
    """翻倍节点：将数字乘以 2"""
    
    node_type = "Double"
    
    def __init__(self, node_id=None, config=None):
        super().__init__(node_id, config)
        from deepeye.nodes.io import NodeInputPort
        self.input_ports = [
            NodeInputPort(name="data", label="数据输入", required=True)
        ]
        self.output_ports = [
            NodeOutputPort(name="output", label="输出")
        ]
    
    def execute(self, inputs: dict) -> dict:
        input_data = self.get_single_input(inputs)
        x = input_data.get("x", 0)
        result = x * 2
        return self.create_single_output(data={"x": result})


class SquareNode(BaseNode):
    """平方节点：将数字平方"""
    
    node_type = "Square"
    
    def __init__(self, node_id=None, config=None):
        super().__init__(node_id, config)
        from deepeye.nodes.io import NodeInputPort
        self.input_ports = [
            NodeInputPort(name="data", label="数据输入", required=True)
        ]
        self.output_ports = [
            NodeOutputPort(name="output", label="输出")
        ]
    
    def execute(self, inputs: dict) -> dict:
        input_data = self.get_single_input(inputs)
        x = input_data.get("x", 0)
        result = x ** 2
        return self.create_single_output(data={"x": result})


def example_3_node_chaining():
    """示例 3: 节点链式执行"""
    print("=" * 60)
    print("示例 3: 节点链式执行")
    print("=" * 60)
    
    # 创建节点
    double_node = DoubleNode()
    square_node = SquareNode()
    
    # 初始输入
    initial_value = 3
    print(f"初始值: {initial_value}")
    
    # 执行第一个节点（翻倍）
    inputs1 = {"data": NodeInput(data={"x": initial_value})}
    outputs1 = double_node.run(inputs1)
    output1 = outputs1["output"]
    print(f"翻倍后: {output1.data['x']}")
    
    # 将第一个节点的输出作为第二个节点的输入（平方）
    inputs2 = {"data": NodeInput(data=output1.data)}
    outputs2 = square_node.run(inputs2)
    output2 = outputs2["output"]
    print(f"平方后: {output2.data['x']}")
    
    print(f"\n结果: (3 × 2)² = {output2.data['x']}")
    print()


# ========== 示例 4: 错误处理 ==========

class DivideNode(BaseNode):
    """除法节点：执行除法运算"""
    
    node_type = "Divide"
    
    def __init__(self, node_id=None, config=None):
        super().__init__(node_id, config)
        from deepeye.nodes.io import NodeInputPort
        self.input_ports = [
            NodeInputPort(name="data", label="数据输入", required=True)
        ]
        self.output_ports = [
            NodeOutputPort(name="output", label="输出")
        ]
    
    def execute(self, inputs: dict) -> dict:
        input_data = self.get_single_input(inputs)
        a = input_data.get("a", 0)
        b = input_data.get("b", 1)
        
        if b == 0:
            raise ValueError("除数不能为零！")
        
        result = a / b
        return self.create_single_output(data={"result": result})


def example_4_error_handling():
    """示例 4: 错误处理"""
    print("=" * 60)
    print("示例 4: 错误处理")
    print("=" * 60)
    
    node = DivideNode()
    
    # 正常情况
    print("正常情况: 10 ÷ 2")
    inputs = {"data": NodeInput(data={"a": 10, "b": 2})}
    outputs = node.run(inputs)
    output = outputs["output"]
    if output.is_success():
        print(f"结果: {output.data['result']}")
    print()
    
    # 错误情况（除以零）
    print("错误情况: 10 ÷ 0")
    inputs = {"data": NodeInput(data={"a": 10, "b": 0})}
    outputs = node.run(inputs)
    output = outputs["output"]
    if output.is_failed():
        print(f"执行失败！")
        print(f"错误信息: {output.error}")
    print()


# ========== 主函数 ==========

def main():
    """运行所有示例"""
    print("\n")
    print("🚀 DeepEye 节点系统使用示例")
    print("=" * 60)
    print()
    
    # 运行所有示例
    example_1_basic_node()
    example_2_node_registry()
    example_3_node_chaining()
    example_4_error_handling()
    
    print("=" * 60)
    print("✅ 所有示例执行完成！")
    print()


if __name__ == "__main__":
    main()



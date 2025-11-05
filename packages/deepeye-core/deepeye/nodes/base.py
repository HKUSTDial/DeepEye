"""基础节点类

定义所有节点的抽象基类。
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type
from uuid import uuid4
from pydantic import BaseModel, Field, ConfigDict

from deepeye.nodes.io import (
    NodeInput,
    NodeOutput,
    NodeInputPort,
    NodeOutputPort,
    NodeStatus,
)
from deepeye.exceptions import NodeExecutionError, NodeValidationError


class NodeConfig(BaseModel):
    """节点配置基类
    
    每个节点可以继承此类来定义自己的配置结构。
    
    Example:
        >>> class MyNodeConfig(NodeConfig):
        ...     host: str = "localhost"
        ...     port: int = 5432
    """
    
    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)


class NodeMetadata(BaseModel):
    """节点元数据
    
    描述节点的基本信息和能力。
    
    Attributes:
        name: 节点名称
        display_name: 显示名称
        description: 节点描述
        category: 节点类别（如 datasource, processing, visualization 等）
        tags: 节点标签
        version: 节点版本
        author: 节点作者
        
        # Agent 编排相关的语义信息
        semantic_description: 详细的语义描述，供 Agent 理解节点功能
        capabilities: 能力标签列表，描述节点能做什么
        input_description: 输入端口的详细描述
        output_description: 输出端口的详细描述
        use_cases: 典型使用场景列表
        examples: 使用示例列表
    """
    
    model_config = ConfigDict(extra="allow")
    
    name: str = Field(
        description="节点类型名称（唯一标识）"
    )
    display_name: str = Field(
        default="",
        description="节点显示名称"
    )
    description: str = Field(
        default="",
        description="节点功能描述"
    )
    category: str = Field(
        default="general",
        description="节点类别"
    )
    tags: List[str] = Field(
        default_factory=list,
        description="节点标签"
    )
    version: str = Field(
        default="0.1.0",
        description="节点版本"
    )
    author: str = Field(
        default="",
        description="节点作者"
    )
    
    # ========== Agent 编排相关的语义信息 ==========
    semantic_description: str = Field(
        default="",
        description="详细的语义描述，用于 Agent 理解节点功能和使用场景"
    )
    capabilities: List[str] = Field(
        default_factory=list,
        description="能力标签列表，如 ['filter', 'transform', 'aggregate']"
    )
    input_description: Dict[str, str] = Field(
        default_factory=dict,
        description="输入端口的详细描述，键为端口名，值为描述"
    )
    output_description: Dict[str, str] = Field(
        default_factory=dict,
        description="输出端口的详细描述，键为端口名，值为描述"
    )
    use_cases: List[str] = Field(
        default_factory=list,
        description="典型使用场景列表"
    )
    examples: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="使用示例列表，每个示例包含 task/input/output"
    )


class BaseNode(ABC):
    """基础节点抽象类
    
    所有节点都必须继承此类并实现 execute 方法。
    
    Attributes:
        node_type: 节点类型（类变量）
        metadata: 节点元数据
        input_ports: 输入端口列表
        output_ports: 输出端口列表
        
    Example:
        >>> class PrintNode(BaseNode):
        ...     node_type = "Print"
        ...     
        ...     def __init__(self, node_id: Optional[str] = None, config: Optional[Dict] = None):
        ...         super().__init__(node_id, config)
        ...         self.metadata = NodeMetadata(
        ...             name="Print",
        ...             display_name="打印节点",
        ...             description="打印输入数据"
        ...         )
        ...     
        ...     def execute(self, inputs: NodeInput) -> NodeOutput:
        ...         print(inputs.data)
        ...         return NodeOutput(data=inputs.data)
    """
    
    # 节点类型（子类必须定义）
    node_type: str = "BaseNode"
    
    def __init__(
        self,
        node_id: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> None:
        """初始化节点
        
        Args:
            node_id: 节点实例ID（唯一标识），如果为None则自动生成
            config: 节点配置字典（会与全局配置合并，优先级高于全局配置）
        
        Note:
            配置优先级（从高到低）：
            1. init 方法的 config 参数（显式传递）
            2. 全局配置（GlobalConfig）
            3. 节点的默认值
        """
        self.node_id = node_id or str(uuid4())
        
        # 合并全局配置和用户配置
        merged_config = self._merge_global_config(config)
        self.config = self._parse_config(merged_config)
        
        # 节点元数据（子类应该在__init__中设置）
        self.metadata = NodeMetadata(name=self.node_type)
        
        # 输入输出端口（子类可以在__init__中定义）
        self.input_ports: List[NodeInputPort] = []
        self.output_ports: List[NodeOutputPort] = []
        
        # 执行状态
        self._status = NodeStatus.PENDING
        self._outputs: Dict[str, NodeOutput] = {}
    
    def _merge_global_config(self, user_config: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """合并全局配置和用户配置
        
        配置优先级：user_config > global_config > node defaults
        
        Args:
            user_config: 用户提供的配置
        
        Returns:
            合并后的配置字典
        """
        try:
            from deepeye.config import get_global_config
            global_config_manager = get_global_config()
            return global_config_manager.merge_with_config(self.node_type, user_config)
        except ImportError:
            # 如果全局配置模块不可用，直接返回用户配置
            return user_config or {}
    
    def _parse_config(self, config: Dict[str, Any]) -> NodeConfig:
        """解析配置
        
        Args:
            config: 配置字典
            
        Returns:
            NodeConfig对象
        """
        # 默认使用基础配置类，子类可以重写此方法来使用自定义配置类
        return NodeConfig(**config)
    
    @abstractmethod
    def execute(self, inputs: Dict[str, NodeInput]) -> Dict[str, NodeOutput]:
        """执行节点逻辑（抽象方法，子类必须实现）
        
        Args:
            inputs: 输入端口名称到输入数据的映射
                例如: {"data": NodeInput(...), "config": NodeInput(...)}
                对于只有一个输入端口的节点，可以只有一个键值对
            
        Returns:
            输出端口名称到输出数据的映射
            例如: {"output": NodeOutput(...)} 或
                  {"result": NodeOutput(...), "metadata": NodeOutput(...)}
            
        Raises:
            NodeExecutionError: 节点执行失败
            
        Note:
            - 对于单输入场景，可以使用 get_single_input() 辅助方法
            - 对于单输出场景，可以使用 create_single_output() 辅助方法
        """
        pass
    
    def validate_inputs(self, inputs: Dict[str, NodeInput]) -> None:
        """验证输入数据
        
        Args:
            inputs: 输入端口名称到输入数据的映射
            
        Raises:
            NodeValidationError: 输入验证失败
        """
        errors = []
        
        # 检查所有必需端口是否都有输入
        for port in self.input_ports:
            if port.required and port.name not in inputs:
                errors.append(f"缺少必需的输入端口: '{port.name}'")
            elif port.name in inputs:
                # 验证该端口的输入数据
                is_valid, port_errors = port.validate_input(inputs[port.name])
                if not is_valid:
                    errors.extend([f"端口 '{port.name}': {err}" for err in port_errors])
        
        # 检查是否有未定义的输入端口
        defined_port_names = {port.name for port in self.input_ports}
        for input_name in inputs.keys():
            if input_name not in defined_port_names:
                errors.append(f"未定义的输入端口: '{input_name}'")
        
        if errors:
            raise NodeValidationError(
                f"节点 {self.node_id} ({self.node_type}) 输入验证失败:\n" +
                "\n".join(f"  - {error}" for error in errors)
            )
    
    def validate_outputs(self, outputs: Dict[str, NodeOutput]) -> None:
        """验证输出数据
        
        Args:
            outputs: 输出端口名称到输出数据的映射
            
        Raises:
            NodeValidationError: 输出验证失败
        """
        errors = []
        
        # 检查所有定义的输出端口是否都有输出
        for port in self.output_ports:
            if port.name not in outputs:
                errors.append(f"缺少输出端口: '{port.name}'")
        
        # 检查是否有未定义的输出端口
        defined_port_names = {port.name for port in self.output_ports}
        for output_name in outputs.keys():
            if output_name not in defined_port_names:
                errors.append(f"未定义的输出端口: '{output_name}'")
        
        if errors:
            raise NodeValidationError(
                f"节点 {self.node_id} ({self.node_type}) 输出验证失败:\n" +
                "\n".join(f"  - {error}" for error in errors)
            )
    
    def get_single_input(self, inputs: Dict[str, NodeInput]) -> NodeInput:
        """获取单个输入（用于只有一个输入端口的简单场景）
        
        Args:
            inputs: 输入字典
            
        Returns:
            第一个输入端口的数据
            
        Raises:
            ValueError: 如果输入为空或有多个输入
            
        Example:
            >>> def execute(self, inputs: Dict[str, NodeInput]) -> NodeOutput:
            ...     input_data = self.get_single_input(inputs)  # 便捷方法
            ...     result = self.process(input_data.data)
            ...     return NodeOutput(data=result)
        """
        if not inputs:
            raise ValueError("没有输入数据")
        if len(inputs) > 1:
            raise ValueError(f"期望单个输入，但收到 {len(inputs)} 个输入")
        return next(iter(inputs.values()))
    
    def get_single_output(self, outputs: Dict[str, NodeOutput]) -> NodeOutput:
        """获取单个输出（用于只有一个输出端口的简单场景）
        
        Args:
            outputs: 输出字典
            
        Returns:
            唯一的输出数据
            
        Raises:
            ValueError: 如果输出为空或有多个输出
        """
        if not outputs:
            raise ValueError("没有输出数据")
        if len(outputs) > 1:
            raise ValueError(f"期望单个输出，但收到 {len(outputs)} 个输出")
        return next(iter(outputs.values()))
    
    def create_single_output(
        self,
        data: Any = None,
        port_name: Optional[str] = None,
        **kwargs
    ) -> Dict[str, NodeOutput]:
        """创建单输出的便捷方法
        
        Args:
            data: 输出数据
            port_name: 输出端口名称（可选，如果未指定则使用节点的输出端口名）
            **kwargs: NodeOutput 的其他参数
            
        Returns:
            包含单个输出的字典
        """
        # 确定端口名称
        if port_name is None:
            if len(self.output_ports) == 1:
                port_name = self.output_ports[0].name
            elif len(self.output_ports) == 0:
                port_name = "output"  # 默认端口名
            else:
                raise ValueError(
                    f"节点有多个输出端口，必须指定 port_name。"
                    f"可用端口: {[p.name for p in self.output_ports]}"
                )
        
        return {port_name: NodeOutput(data=data, **kwargs)}
    
    def run(self, inputs: Dict[str, NodeInput]) -> Dict[str, NodeOutput]:
        """运行节点（包含验证和异常处理）
        
        Args:
            inputs: 输入端口名称到输入数据的映射
                例如: {"data": NodeInput(...)}
                对于简单节点，通常只有一个输入端口
            
        Returns:
            输出端口名称到输出数据的映射
            例如: {"output": NodeOutput(...)} 或
                  {"result": NodeOutput(...), "logs": NodeOutput(...)}
        """
        # 准备基础日志
        execution_logs = []
        base_metadata = {"node_id": self.node_id, "node_type": self.node_type}
        
        try:
            # 更新状态
            self._status = NodeStatus.RUNNING
            
            # 验证输入
            self.validate_inputs(inputs)
            execution_logs.append(f"输入验证通过")
            
            # 执行节点逻辑
            execution_logs.append(f"开始执行节点: {self.node_type}")
            results = self.execute(inputs)
            
            # 验证输出
            self.validate_outputs(results)
            execution_logs.append(f"输出验证通过")
            
            # 为每个输出端口添加日志和元数据
            for port_name, output in results.items():
                # 添加日志（根据输出状态决定）
                if output.status == NodeStatus.FAILED:
                    output.add_log(f"节点执行失败")
                else:
                    output.add_log(f"节点执行成功")
                    # 只有当输出没有显式设置状态时，才设置为 SUCCESS
                    if output.status not in [NodeStatus.SUCCESS, NodeStatus.FAILED]:
                        output.status = NodeStatus.SUCCESS
                
                # 合并执行日志
                output.logs = execution_logs + output.logs
                
                # 设置元数据
                output.metadata.update(base_metadata)
                output.metadata["port"] = port_name
            
            # 更新节点状态（如果有任何输出失败，则节点失败）
            has_failed = any(output.status == NodeStatus.FAILED for output in results.values())
            self._status = NodeStatus.FAILED if has_failed else NodeStatus.SUCCESS
            self._outputs = results
            
            return results
            
        except (NodeValidationError, Exception) as e:
            # 创建错误输出
            error_msg = (
                f"输入验证失败: {str(e)}" if isinstance(e, NodeValidationError)
                else f"节点执行失败: {type(e).__name__}: {str(e)}"
            )
            
            # 确定输出端口名称（用于错误情况）
            if len(self.output_ports) == 1:
                error_port_name = self.output_ports[0].name
            elif len(self.output_ports) == 0:
                error_port_name = "output"
            else:
                # 多个输出端口时，为每个端口创建错误输出
                error_outputs = {}
                for port in self.output_ports:
                    error_output = NodeOutput(
                        status=NodeStatus.FAILED,
                        error=error_msg,
                        metadata=base_metadata.copy()
                    )
                    error_output.logs = execution_logs.copy()
                    error_output.metadata["port"] = port.name
                    error_outputs[port.name] = error_output
                
                self._status = NodeStatus.FAILED
                self._outputs = error_outputs
                return error_outputs
            
            # 单个输出端口的错误处理
            error_output = NodeOutput(
                status=NodeStatus.FAILED,
                error=error_msg,
                metadata=base_metadata
            )
            error_output.logs = execution_logs
            error_output.metadata["port"] = error_port_name
            
            self._status = NodeStatus.FAILED
            error_outputs = {error_port_name: error_output}
            self._outputs = error_outputs
            return error_outputs
    
    def get_status(self) -> NodeStatus:
        """获取节点执行状态
        
        Returns:
            节点状态
        """
        return self._status
    
    def get_outputs(self) -> Dict[str, NodeOutput]:
        """获取所有输出端口的输出
        
        Returns:
            输出端口名称到输出数据的映射，如果尚未执行则返回空字典
        """
        return self._outputs
    
    def get_output(self, port_name: Optional[str] = None) -> Optional[NodeOutput]:
        """获取指定端口的输出
        
        Args:
            port_name: 输出端口名称。如果为None且只有一个输出端口，则返回该端口的输出
            
        Returns:
            节点输出，如果尚未执行或端口不存在则返回None
        """
        if port_name is None:
            # 如果未指定端口名且只有一个输出，返回该输出
            if len(self._outputs) == 1:
                return next(iter(self._outputs.values()))
            elif len(self._outputs) == 0:
                return None
            else:
                raise ValueError(
                    f"节点有多个输出端口，必须指定 port_name。"
                    f"可用端口: {list(self._outputs.keys())}"
                )
        return self._outputs.get(port_name)
    
    def reset(self) -> None:
        """重置节点状态"""
        self._status = NodeStatus.PENDING
        self._outputs = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典表示
        
        Returns:
            节点信息字典
        """
        return {
            "node_id": self.node_id,
            "node_type": self.node_type,
            "metadata": self.metadata.model_dump(),
            "config": self.config.model_dump() if hasattr(self.config, "model_dump") else {},
            "status": self._status.value,
            "input_ports": [
                {
                    "name": port.name,
                    "label": port.label,
                    "schemas": [schema.model_dump() for schema in port.schemas]
                }
                for port in self.input_ports
            ],
            "output_ports": [
                {
                    "name": port.name,
                    "label": port.label,
                    "schemas": [schema.model_dump() for schema in port.schemas]
                }
                for port in self.output_ports
            ],
        }
    
    def __repr__(self) -> str:
        """字符串表示"""
        return f"<{self.node_type}(id={self.node_id}, status={self._status.value})>"
    
    def __str__(self) -> str:
        """字符串表示"""
        return f"{self.node_type}({self.node_id})"




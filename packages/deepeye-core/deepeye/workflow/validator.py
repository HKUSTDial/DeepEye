"""工作流验证器模块

提供工作流结构和连接的完整性验证功能。
"""

from typing import Dict, List, Any, Optional, Set, TYPE_CHECKING
from dataclasses import dataclass, field

from deepeye.workflow.graph import WorkflowGraph, NodeConnection
from deepeye.nodes import BaseNode
from deepeye.exceptions import WorkflowValidationError

if TYPE_CHECKING:
    from deepeye.runtime.context import ExecutionContext


@dataclass
class ValidationIssue:
    """验证问题
    
    Attributes:
        level: 问题级别 (error, warning, info)
        message: 问题描述
        node_id: 相关节点 ID（可选）
        details: 额外详细信息
    """
    level: str  # "error", "warning", "info"
    message: str
    node_id: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    
    def __str__(self) -> str:
        """字符串表示"""
        prefix = f"[{self.level.upper()}]"
        if self.node_id:
            prefix += f" 节点 '{self.node_id}'"
        return f"{prefix}: {self.message}"


@dataclass
class ValidationReport:
    """验证报告
    
    Attributes:
        is_valid: 是否通过验证
        errors: 错误列表
        warnings: 警告列表
        info: 信息列表
    """
    is_valid: bool = True
    errors: List[ValidationIssue] = field(default_factory=list)
    warnings: List[ValidationIssue] = field(default_factory=list)
    info: List[ValidationIssue] = field(default_factory=list)
    
    def add_error(
        self,
        message: str,
        node_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """添加错误"""
        self.errors.append(ValidationIssue(
            level="error",
            message=message,
            node_id=node_id,
            details=details or {}
        ))
        self.is_valid = False
    
    def add_warning(
        self,
        message: str,
        node_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """添加警告"""
        self.warnings.append(ValidationIssue(
            level="warning",
            message=message,
            node_id=node_id,
            details=details or {}
        ))
    
    def add_info(
        self,
        message: str,
        node_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """添加信息"""
        self.info.append(ValidationIssue(
            level="info",
            message=message,
            node_id=node_id,
            details=details or {}
        ))
    
    def has_errors(self) -> bool:
        """是否有错误"""
        return len(self.errors) > 0
    
    def has_warnings(self) -> bool:
        """是否有警告"""
        return len(self.warnings) > 0
    
    def get_summary(self) -> str:
        """获取摘要"""
        if self.is_valid:
            return "✅ 验证通过"
        return f"❌ 验证失败: {len(self.errors)} 个错误"
    
    def __str__(self) -> str:
        """字符串表示"""
        lines = [self.get_summary()]
        
        if self.errors:
            lines.append(f"\n错误 ({len(self.errors)}):")
            for issue in self.errors:
                lines.append(f"  - {issue}")
        
        if self.warnings:
            lines.append(f"\n警告 ({len(self.warnings)}):")
            for issue in self.warnings:
                lines.append(f"  - {issue}")
        
        if self.info:
            lines.append(f"\n信息 ({len(self.info)}):")
            for issue in self.info:
                lines.append(f"  - {issue}")
        
        return "\n".join(lines)


class WorkflowValidator:
    """工作流验证器
    
    验证工作流的结构完整性、连接有效性等。
    
    Example:
        >>> validator = WorkflowValidator()
        >>> report = validator.validate(graph, nodes)
        >>> if not report.is_valid:
        ...     print(report)
    """
    
    def __init__(self) -> None:
        """初始化验证器"""
        pass
    
    def validate(
        self,
        graph: WorkflowGraph,
        nodes: Dict[str, BaseNode],
        context: Optional["ExecutionContext"] = None
    ) -> ValidationReport:
        """执行完整验证
        
        Args:
            graph: 工作流图
            nodes: 节点实例字典 {node_id: node_instance}
            context: 执行上下文（可选，用于检查静态输入）
            
        Returns:
            验证报告
        """
        report = ValidationReport()
        
        # 1. 验证图结构
        self._validate_graph_structure(graph, report)
        
        # 2. 验证节点存在性
        self._validate_nodes_exist(graph, nodes, report)
        
        # 3. 验证连接有效性
        self._validate_connections(graph, nodes, report)
        
        # 4. 检查孤立节点
        self._check_isolated_nodes(graph, report)
        
        # 5. 检查必需输入
        self._validate_required_inputs(graph, nodes, report, context)
        
        return report
    
    def _validate_graph_structure(
        self,
        graph: WorkflowGraph,
        report: ValidationReport
    ) -> None:
        """验证图结构
        
        检查图是否为 DAG，是否有循环依赖等。
        """
        # 检查是否为空图
        if graph.is_empty():
            report.add_warning("工作流为空")
            return
        
        # 检查是否为 DAG
        if graph.has_cycle():
            cycle = graph.find_cycle()
            cycle_path = " -> ".join(cycle) if cycle else "未知"
            report.add_error(
                f"工作流包含循环依赖: {cycle_path}",
                details={"cycle": cycle}
            )
    
    def _validate_nodes_exist(
        self,
        graph: WorkflowGraph,
        nodes: Dict[str, BaseNode],
        report: ValidationReport
    ) -> None:
        """验证节点存在性
        
        检查图中的所有节点是否都有对应的节点实例。
        """
        graph_node_ids = set(graph.list_nodes())
        instance_node_ids = set(nodes.keys())
        
        # 检查图中的节点是否都有实例
        missing_instances = graph_node_ids - instance_node_ids
        if missing_instances:
            for node_id in missing_instances:
                report.add_error(
                    f"节点 '{node_id}' 在图中定义但没有实例",
                    node_id=node_id
                )
        
        # 检查是否有多余的实例
        extra_instances = instance_node_ids - graph_node_ids
        if extra_instances:
            for node_id in extra_instances:
                report.add_warning(
                    f"节点 '{node_id}' 有实例但不在图中",
                    node_id=node_id
                )
    
    def _validate_connections(
        self,
        graph: WorkflowGraph,
        nodes: Dict[str, BaseNode],
        report: ValidationReport
    ) -> None:
        """验证连接有效性
        
        检查所有连接的端口是否存在且有效。
        同时检查同一个输入端口是否有多个连接。
        """
        # 记录每个节点的输入端口连接情况
        input_port_connections: Dict[str, Dict[str, List[str]]] = {}  # {node_id: {port_name: [from_node_ids]}}
        
        for from_id, to_id in graph.list_edges():
            connection = graph.get_edge(from_id, to_id)
            
            # 检查源节点
            if from_id not in nodes:
                continue  # 已经在 _validate_nodes_exist 中报告过
            
            from_node = nodes[from_id]
            
            # 检查输出端口是否存在
            output_port_exists = any(
                port.name == connection.from_port
                for port in from_node.output_ports
            )
            if not output_port_exists:
                report.add_error(
                    f"输出端口 '{connection.from_port}' 不存在",
                    node_id=from_id,
                    details={
                        "connection": f"{from_id}.{connection.from_port} -> {to_id}.{connection.to_port}",
                        "available_ports": [p.name for p in from_node.output_ports]
                    }
                )
            
            # 检查目标节点
            if to_id not in nodes:
                continue  # 已经在 _validate_nodes_exist 中报告过
            
            to_node = nodes[to_id]
            
            # 检查输入端口是否存在
            input_port_exists = any(
                port.name == connection.to_port
                for port in to_node.input_ports
            )
            if not input_port_exists:
                report.add_error(
                    f"输入端口 '{connection.to_port}' 不存在",
                    node_id=to_id,
                    details={
                        "connection": f"{from_id}.{connection.from_port} -> {to_id}.{connection.to_port}",
                        "available_ports": [p.name for p in to_node.input_ports]
                    }
                )
            
            # 记录输入端口连接
            if to_id not in input_port_connections:
                input_port_connections[to_id] = {}
            if connection.to_port not in input_port_connections[to_id]:
                input_port_connections[to_id][connection.to_port] = []
            input_port_connections[to_id][connection.to_port].append(from_id)
        
        # 检查是否有输入端口有多个连接
        for node_id, port_connections in input_port_connections.items():
            for port_name, from_nodes in port_connections.items():
                if len(from_nodes) > 1:
                    report.add_error(
                        f"输入端口 '{port_name}' 有 {len(from_nodes)} 个连接，但一个输入端口只能有一个连接",
                        node_id=node_id,
                        details={
                            "port": port_name,
                            "connections_from": from_nodes,
                            "connection_count": len(from_nodes)
                        }
                    )
    
    def _check_isolated_nodes(
        self,
        graph: WorkflowGraph,
        report: ValidationReport
    ) -> None:
        """检查孤立节点
        
        检查是否有既没有输入也没有输出的节点（除了根节点和叶子节点）。
        """
        for node_id in graph.list_nodes():
            predecessors = graph.get_predecessors(node_id)
            successors = graph.get_successors(node_id)
            
            # 完全孤立的节点（既没有输入也没有输出）
            if len(predecessors) == 0 and len(successors) == 0:
                report.add_warning(
                    "节点完全孤立，既没有输入也没有输出",
                    node_id=node_id
                )
    
    def _validate_required_inputs(
        self,
        graph: WorkflowGraph,
        nodes: Dict[str, BaseNode],
        report: ValidationReport,
        context: Optional["ExecutionContext"] = None
    ) -> None:
        """验证必需输入
        
        检查所有节点的必需输入端口是否都有连接或完整的静态输入。
        
        特殊情况处理：
        - 如果节点没有前驱节点，但定义了必需输入端口，检查是否有静态输入
        - 如果有静态输入，验证静态输入是否包含端口所有必需的参数
        - 如果既没有连接也没有静态输入，或静态输入不完整，则报错
        - 如果节点没有前驱节点，也没有必需输入端口，则是合法的根节点
        """
        for node_id, node in nodes.items():
            # 跳过不在图中的节点
            if not graph.has_node(node_id):
                continue
            
            # 获取该节点的所有输入连接
            predecessors = graph.get_predecessors(node_id)
            incoming_connections = []
            
            for pred_id in predecessors:
                conn = graph.get_edge(pred_id, node_id)
                incoming_connections.append(conn)
            
            # 收集已连接的输入端口
            connected_ports = {conn.to_port for conn in incoming_connections}
            
            # 检查所有必需端口
            for port in node.input_ports:
                if port.required and port.name not in connected_ports:
                    # 检查是否有静态输入（从 context 中）
                    has_valid_static_input = False
                    missing_params = []
                    
                    if context is not None:
                        static_input = context.get_node_input(node_id, port.name)
                        if static_input is not None:
                            # 验证静态输入是否包含所有必需的参数
                            for schema in port.schemas:
                                if schema.required:
                                    # 检查静态输入中是否有这个必需参数
                                    value = static_input.get(schema.name, schema.default)
                                    if not schema.validate_value(value):
                                        missing_params.append(schema.name)
                            
                            # 如果所有必需参数都存在且有效，则静态输入是有效的
                            has_valid_static_input = len(missing_params) == 0
                    
                    # 如果有完整且有效的静态输入，跳过验证
                    if has_valid_static_input:
                        continue
                    
                    # 构建错误信息
                    if context is not None and static_input is not None and len(missing_params) > 0:
                        # 有静态输入，但不完整
                        error_msg = (
                            f"端口 '{port.name}' 的静态输入不完整，"
                            f"缺少必需参数: {', '.join(missing_params)}"
                        )
                        details = {
                            "port": port.name,
                            "port_label": port.label,
                            "missing_parameters": missing_params,
                            "required_parameters": [s.name for s in port.schemas if s.required],
                            "is_root_node": len(predecessors) == 0
                        }
                    else:
                        # 完全没有输入
                        if len(predecessors) == 0:
                            # 根节点
                            error_msg = (
                                f"根节点定义了必需的输入端口 '{port.name}' 但没有连接或静态输入。"
                                f"根节点不应该定义必需输入端口，或者需要添加前驱节点或静态输入来提供输入。"
                            )
                            details = {
                                "port": port.name,
                                "port_label": port.label,
                                "is_root_node": True,
                                "required_parameters": [s.name for s in port.schemas if s.required],
                                "suggestion": "将输入端口设为可选(required=False)，或添加前驱节点或静态输入"
                            }
                        else:
                            # 非根节点
                            error_msg = f"必需的输入端口 '{port.name}' 没有连接"
                            details = {
                                "port": port.name,
                                "port_label": port.label,
                                "is_root_node": False,
                                "required_parameters": [s.name for s in port.schemas if s.required]
                            }
                    
                    report.add_error(error_msg, node_id=node_id, details=details)
    
    def validate_and_raise(
        self,
        graph: WorkflowGraph,
        nodes: Dict[str, BaseNode],
        context: Optional["ExecutionContext"] = None
    ) -> None:
        """验证并在失败时抛出异常
        
        Args:
            graph: 工作流图
            nodes: 节点实例字典
            context: 执行上下文（可选，用于检查静态输入）
            
        Raises:
            WorkflowValidationError: 如果验证失败
        """
        report = self.validate(graph, nodes, context)
        
        if not report.is_valid:
            error_messages = [str(issue) for issue in report.errors]
            raise WorkflowValidationError(
                f"工作流验证失败:\n" + "\n".join(error_messages)
            )
    
    def quick_validate(self, graph: WorkflowGraph) -> bool:
        """快速验证（仅检查图结构）
        
        Args:
            graph: 工作流图
            
        Returns:
            是否通过验证
        """
        report = ValidationReport()
        self._validate_graph_structure(graph, report)
        return report.is_valid


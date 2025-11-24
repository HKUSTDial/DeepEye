"""Node service for managing node operations."""

import base64
import time
from typing import Any, Dict, List, Optional

from deepeye.nodes import NodeInput, NodeOutput, get_registry
from deepeye.exceptions import NodeError

from app.models.schemas.node import (
    NodeInfo,
    NodeListItem,
    NodeListResponse,
    NodeExecutionResult,
)


class NodeService:
    """Node service for managing node operations."""

    def __init__(self):
        """Initialize node service."""
        self.registry = get_registry()

    def get_all_nodes(self) -> NodeListResponse:
        """Get all registered nodes."""
        node_types = self.registry.list_node_types()
        nodes = []

        for node_type in node_types:
            try:
                node_info = self.registry.get_node_info(node_type)
                metadata = node_info.get("metadata", {})
                
                nodes.append(
                    NodeListItem(
                        node_type=node_type,
                        display_name=metadata.get("display_name", node_type),
                        description=metadata.get("description", ""),
                        version=metadata.get("version", "0.1.0"),
                    )
                )
            except Exception as e:
                # Skip nodes that can't be instantiated
                continue

        return NodeListResponse(total=len(nodes), nodes=nodes)

    def get_node_info(self, node_type: str) -> Optional[NodeInfo]:
        """Get detailed information about a node."""
        if not self.registry.is_registered(node_type):
            return None

        try:
            node_info_dict = self.registry.get_node_info(node_type)
            
            # print(node_info_dict)
            
            # Convert metadata
            metadata_dict = node_info_dict.get("metadata", {})
            from app.models.schemas.node import NodeMetadata
            
            metadata = NodeMetadata(
                name=metadata_dict.get("name", node_type),
                display_name=metadata_dict.get("display_name", node_type),
                description=metadata_dict.get("description", ""),
                version=metadata_dict.get("version", "0.1.0"),
                author=metadata_dict.get("author", ""),
            )
            
            # Convert ports
            from app.models.schemas.node import NodePort
            
            input_ports = [
                NodePort(**port) for port in node_info_dict.get("input_ports", [])
            ]
            output_ports = [
                NodePort(**port) for port in node_info_dict.get("output_ports", [])
            ]
            
            return NodeInfo(
                node_type=node_type,
                class_name=node_info_dict.get("class_name", ""),
                metadata=metadata,
                input_ports=input_ports,
                output_ports=output_ports,
            )
        except Exception as e:
            return None

    async def execute_node(
        self,
        node_type: str,
        inputs: Dict[str, Any],
        config: Optional[Dict[str, Any]] = None,
    ) -> NodeExecutionResult:
        """Execute a single node."""
        if not self.registry.is_registered(node_type):
            return NodeExecutionResult(
                status="failed",
                outputs={},
                execution_time=0.0,
                error=f"Node type '{node_type}' not found",
            )

        start_time = time.time()

        try:
            # Create node instance
            node = self.registry.create_node(node_type, config=config or {})

            # Prepare inputs
            node_inputs = {}
            for port_name, value in inputs.items():
                # Create NodeInput from raw value
                node_inputs[port_name] = NodeInput(data=value)

            # Execute node
            outputs = node.run(node_inputs)

            # Check if any output has failed
            has_error = any(
                output.is_failed() for output in outputs.values()
            )

            if has_error:
                # Extract error message from failed output
                error_output = next(
                    output for output in outputs.values() if output.is_failed()
                )

                error_msg = error_output.error
                if not error_msg and error_output.metadata:
                    error_msg = error_output.metadata.get("error")
                if not error_msg:
                    error_msg = "Node execution failed"

                execution_time = time.time() - start_time

                print(f"❌ Node execution failed: {node_type}")
                print(f"   Error: {error_msg}")
                print(f"   Output metadata: {error_output.metadata}")

                return NodeExecutionResult(
                    status="failed",
                    outputs={},
                    execution_time=execution_time,
                    error=error_msg,
                )

            # Serialize outputs
            serialized_outputs = self._serialize_outputs(outputs)

            execution_time = time.time() - start_time

            return NodeExecutionResult(
                status="success",
                outputs=serialized_outputs,
                execution_time=execution_time,
                error=None,
            )
        except Exception as e:
            execution_time = time.time() - start_time

            import traceback
            print(f"❌ Node execution exception: {node_type}")
            print(f"   Error: {str(e)}")
            print(f"   Traceback:")
            traceback.print_exc()

            return NodeExecutionResult(
                status="failed",
                outputs={},
                execution_time=execution_time,
                error=str(e),
            )

    def _serialize_outputs(self, outputs: Dict[str, NodeOutput]) -> Dict[str, Any]:
        """Serialize node outputs for API response."""
        serialized = {}
        for name, output in outputs.items():
            serialized[name] = self._serialize_value(output.data)
        return serialized

    def _serialize_value(self, value: Any) -> Any:
        """Serialize a single value."""
        # Handle bytes
        if isinstance(value, bytes):
            try:
                return base64.b64encode(value).decode('utf-8')
            except Exception as e:
                print(f"⚠️  cant serialize bytes: {e}")
                return None

        # Handle pandas DataFrame
        if hasattr(value, "shape") and hasattr(value, "columns"):
            try:
                return {
                    "type": "DataFrame",
                    "shape": list(value.shape),
                    "columns": list(value.columns),
                    "preview": value.head(10).to_dict("records"),
                }
            except Exception:
                return {"type": "DataFrame", "shape": list(value.shape), "columns": list(value.columns)}

        # Handle dict (recursively serialize nested values)
        if isinstance(value, dict):
            return {k: self._serialize_value(v) for k, v in value.items()}

        # Handle list (recursively serialize elements)
        if isinstance(value, list):
            return [self._serialize_value(item) for item in value]

        # Handle other types
        return value


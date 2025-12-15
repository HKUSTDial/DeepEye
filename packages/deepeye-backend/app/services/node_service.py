"""Node service for managing node operations."""

import base64
import time
from typing import Any, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from deepeye.nodes import NodeInput, NodeOutput, get_registry
from deepeye.exceptions import NodeError

from app.models.schemas.node import (
    NodeInfo,
    NodeListItem,
    NodeListResponse,
    NodeExecutionResult,
)
from app.services.connection_service import ConnectionService
from app.services.llm_service import LLMService


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
        db: Optional[AsyncSession] = None,
        user_id: Optional[str] = None,
    ) -> NodeExecutionResult:
        """Execute a single node."""
        if not self.registry.is_registered(node_type):
            return NodeExecutionResult(
                status="failed",
                outputs={},
                execution_time=0.0,
                error=f"Node type '{node_type}' not found",
            )

        # Resolve database connection if needed
        if node_type == "DatabaseDataSource" and config and "database_id" in config and db and user_id:
            try:
                connection_service = ConnectionService()
                conn = await connection_service.get_connection_by_id(db, config["database_id"], user_id)
                if conn:
                    # Construct connection string
                    connection_string = self._build_connection_string(conn)
                    config["connection_string"] = connection_string
                else:
                    return NodeExecutionResult(
                        status="failed",
                        outputs={},
                        execution_time=0.0,
                        error=f"Database connection not found: {config['database_id']}",
                    )
            except Exception as e:
                return NodeExecutionResult(
                    status="failed",
                    outputs={},
                    execution_time=0.0,
                    error=f"Failed to resolve database connection: {str(e)}",
                )

        # Resolve LLM model if needed
        if node_type in ["NL2SQL", "DataCoder", "DataPlot"] and config and ("model_id" in config or "model" in config) and db and user_id:
            model_key = "model_id" if "model_id" in config else "model"
            try:
                llm_service = LLMService()
                llm = await llm_service.get_llm_model_by_id(db, config[model_key], user_id)
                if llm:
                    config["api_key"] = llm.api_key
                    config["base_url"] = llm.base_url
                    config["model"] = llm.model_name or llm.model_endpoint_name
                else:
                    return NodeExecutionResult(
                        status="failed",
                        outputs={},
                        execution_time=0.0,
                        error=f"LLM model not found: {config[model_key]}",
                    )
            except Exception as e:
                # If model_key is a valid model name (not a UUID), we might want to let it pass
                # But here we assume frontend always sends IDs from the selector
                return NodeExecutionResult(
                    status="failed",
                    outputs={},
                    execution_time=0.0,
                    error=f"Failed to resolve LLM model: {str(e)}",
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

    def _build_connection_string(self, conn) -> str:
        """Build database connection string from connection object."""
        db_type = conn.type.lower()
        
        if db_type == "sqlite":
             # SQLite path handling might need adjustment based on where files are stored
             # Assuming conn.database is the path
             return f"sqlite:///{conn.database}"
        elif db_type == "mysql":
             return f"mysql+pymysql://{conn.username}:{conn.password}@{conn.host}:{conn.port}/{conn.database}"
        elif db_type in ["postgresql", "postgres"]:
             return f"postgresql://{conn.username}:{conn.password}@{conn.host}:{conn.port}/{conn.database}"
        
        raise ValueError(f"Unsupported database type: {conn.type}")

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
        # Check for numpy types
        if hasattr(value, "item"):
            try:
                return value.item()
            except Exception:
                pass
        
        return value


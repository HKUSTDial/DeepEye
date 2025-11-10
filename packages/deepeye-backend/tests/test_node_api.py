"""Tests for Node API endpoints."""

import pytest
from fastapi import status

from deepeye.nodes import (
    BaseNode,
    NodeInput,
    NodeOutput,
    register_node,
    get_registry,
)
from deepeye.nodes.io import NodeInputPort, NodeOutputPort, NodeInputSchema, NodeOutputSchema
from deepeye.nodes.base import NodeMetadata


# ========== Test Node Classes ==========

class MockGreetingNode(BaseNode):
    """Test greeting node for API testing."""
    
    node_type = "MockGreeting"
    
    def __init__(self, node_id=None, config=None, validate_on_init=False):
        super().__init__(node_id, config, validate_on_init)
        
        self.metadata = NodeMetadata(
            name="MockGreeting",
            display_name="Test Greeting Node",
            description="A test node that greets users",
            version="1.0.0",
            author="Test Author",
        )
        
        self.input_ports = [
            NodeInputPort(
                name="name",
                label="Name",
                schemas=[
                    NodeInputSchema(
                        name="name",
                        type="string",
                        required=True,
                        description="Name to greet"
                    )
                ]
            )
        ]
        
        self.output_ports = [
            NodeOutputPort(
                name="greeting",
                label="Greeting",
                schemas=[
                    NodeOutputSchema(
                        name="greeting",
                        type="string",
                        description="Generated greeting"
                    )
                ]
            )
        ]
    
    def execute(self, inputs: dict) -> dict:
        """Execute the greeting node."""
        name_input = inputs.get("name", NodeInput())
        # Extract name from input data
        if isinstance(name_input, NodeInput):
            name_data = name_input.data
            if isinstance(name_data, dict):
                name = name_data.get("name", "World")
            else:
                name = name_data if name_data else "World"
        else:
            name = "World"
        
        greeting = f"Hello, {name}!"
        
        return {
            "greeting": NodeOutput(data={"greeting": greeting})
        }


class MockAddNode(BaseNode):
    """Test addition node for API testing."""
    
    node_type = "MockAdd"
    
    def __init__(self, node_id=None, config=None, validate_on_init=False):
        super().__init__(node_id, config, validate_on_init)
        
        self.metadata = NodeMetadata(
            name="MockAdd",
            display_name="Test Add Node",
            description="A test node that adds two numbers",
            version="1.0.0",
            author="Test Author",
        )
        
        self.input_ports = [
            NodeInputPort(
                name="a",
                label="First Number",
                schemas=[
                    NodeInputSchema(
                        name="a",
                        type="number",
                        required=True,
                        description="First number"
                    )
                ]
            ),
            NodeInputPort(
                name="b",
                label="Second Number",
                schemas=[
                    NodeInputSchema(
                        name="b",
                        type="number",
                        required=True,
                        description="Second number"
                    )
                ]
            )
        ]
        
        self.output_ports = [
            NodeOutputPort(
                name="result",
                label="Result",
                schemas=[
                    NodeOutputSchema(
                        name="result",
                        type="number",
                        description="Sum of a and b"
                    )
                ]
            )
        ]
    
    def execute(self, inputs: dict) -> dict:
        """Execute the addition node."""
        a_input = inputs.get("a", NodeInput())
        b_input = inputs.get("b", NodeInput())
        
        # Extract values from inputs
        if isinstance(a_input, NodeInput):
            a_data = a_input.data
            a = a_data.get("a", 0) if isinstance(a_data, dict) else (a_data if a_data is not None else 0)
        else:
            a = 0
            
        if isinstance(b_input, NodeInput):
            b_data = b_input.data
            b = b_data.get("b", 0) if isinstance(b_data, dict) else (b_data if b_data is not None else 0)
        else:
            b = 0
        
        result = a + b
        
        return {
            "result": NodeOutput(data={"result": result})
        }


class MockErrorNode(BaseNode):
    """Test node that always raises an error."""
    
    node_type = "MockError"
    
    def __init__(self, node_id=None, config=None, validate_on_init=False):
        super().__init__(node_id, config, validate_on_init)
        
        self.metadata = NodeMetadata(
            name="MockError",
            display_name="Test Error Node",
            description="A test node that always fails",
            version="1.0.0",
        )
        
        self.input_ports = []
        self.output_ports = []
    
    def execute(self, inputs: dict) -> dict:
        """Execute the error node."""
        raise ValueError("This node always fails for testing purposes")


class MockConfigNode(BaseNode):
    """Test node that uses config for prefix."""
    
    node_type = "MockConfig"
    
    def __init__(self, node_id=None, config=None, validate_on_init=False):
        super().__init__(node_id, config, validate_on_init)
        
        self.metadata = NodeMetadata(
            name="MockConfig",
            display_name="Test Config Node",
            description="A test node that uses config",
            version="1.0.0",
        )
        
        self.input_ports = [
            NodeInputPort(
                name="message",
                label="Message",
                schemas=[
                    NodeInputSchema(
                        name="message",
                        type="string",
                        required=True,
                        description="Message to prefix"
                    )
                ]
            )
        ]
        
        self.output_ports = [
            NodeOutputPort(
                name="output",
                label="Output",
                schemas=[
                    NodeOutputSchema(
                        name="output",
                        type="string",
                        description="Prefixed message"
                    )
                ]
            )
        ]
    
    def execute(self, inputs: dict) -> dict:
        """Execute the config node."""
        message_input = inputs.get("message", NodeInput())
        if isinstance(message_input, NodeInput):
            message_data = message_input.data
            message = message_data.get("message", "") if isinstance(message_data, dict) else (message_data if message_data else "")
        else:
            message = ""
        
        # Get prefix from config (with default)
        prefix = getattr(self.config, "prefix", "Default")
        output = f"{prefix}: {message}"
        
        return {
            "output": NodeOutput(data={"output": output})
        }


@pytest.fixture(autouse=True)
def setup_test_nodes():
    """Setup test nodes before each test and cleanup after."""
    registry = get_registry()
    
    # Register test nodes
    register_node(MockGreetingNode)
    register_node(MockAddNode)
    register_node(MockErrorNode)
    register_node(MockConfigNode)
    
    yield
    
    # Cleanup: unregister test nodes
    try:
        registry.unregister("MockGreeting")
    except Exception:
        pass
    try:
        registry.unregister("MockAdd")
    except Exception:
        pass
    try:
        registry.unregister("MockError")
    except Exception:
        pass
    try:
        registry.unregister("MockConfig")
    except Exception:
        pass


class TestNodeAPI:
    """Test Node API endpoints."""

    @pytest.mark.asyncio
    async def test_list_nodes_success(self, async_client):
        """Test successful listing of all nodes."""
        response = await async_client.get("/api/v1/nodes")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "total" in data
        assert "nodes" in data
        assert isinstance(data["nodes"], list)
        assert data["total"] >= 3  # At least our test nodes
        
        # Check that test nodes are in the list
        node_types = [node["node_type"] for node in data["nodes"]]
        assert "MockGreeting" in node_types
        assert "MockAdd" in node_types
        
        # Check node list item structure
        test_node = next(node for node in data["nodes"] if node["node_type"] == "MockGreeting")
        assert "node_type" in test_node
        assert "display_name" in test_node
        assert "description" in test_node
        assert "version" in test_node
        assert test_node["display_name"] == "Test Greeting Node"

    @pytest.mark.asyncio
    async def test_get_node_info_success(self, async_client):
        """Test successful retrieval of node information."""
        response = await async_client.get("/api/v1/nodes/MockGreeting")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["node_type"] == "MockGreeting"
        assert data["class_name"] == "MockGreetingNode"
        assert "metadata" in data
        assert "input_ports" in data
        assert "output_ports" in data
        
        # Check metadata
        metadata = data["metadata"]
        assert metadata["name"] == "MockGreeting"
        assert metadata["display_name"] == "Test Greeting Node"
        assert metadata["description"] == "A test node that greets users"
        assert metadata["version"] == "1.0.0"
        assert metadata["author"] == "Test Author"
        
        # Check input ports
        assert len(data["input_ports"]) == 1
        input_port = data["input_ports"][0]
        assert input_port["name"] == "name"
        assert input_port["label"] == "Name"
        assert len(input_port["schemas"]) == 1
        
        # Check output ports
        assert len(data["output_ports"]) == 1
        output_port = data["output_ports"][0]
        assert output_port["name"] == "greeting"
        assert output_port["label"] == "Greeting"

    @pytest.mark.asyncio
    async def test_get_node_info_not_found(self, async_client):
        """Test getting information for non-existent node."""
        response = await async_client.get("/api/v1/nodes/NonExistentNode")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "detail" in data
        assert "NonExistentNode" in data["detail"]

    @pytest.mark.asyncio
    async def test_execute_node_success(self, async_client):
        """Test successful node execution."""
        request_data = {
            "inputs": {
                "name": {"name": "Alice"}
            }
        }
        
        response = await async_client.post(
            "/api/v1/nodes/MockGreeting/execute",
            json=request_data
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["status"] == "success"
        assert "outputs" in data
        assert "execution_time" in data
        assert data["error"] is None
        
        # Check outputs
        assert "greeting" in data["outputs"]
        greeting_data = data["outputs"]["greeting"]
        assert greeting_data["greeting"] == "Hello, Alice!"
        
        # Check execution time is reasonable
        assert data["execution_time"] >= 0

    @pytest.mark.asyncio
    async def test_execute_node_with_multiple_inputs(self, async_client):
        """Test node execution with multiple inputs."""
        request_data = {
            "inputs": {
                "a": {"a": 5},
                "b": {"b": 3}
            }
        }
        
        response = await async_client.post(
            "/api/v1/nodes/MockAdd/execute",
            json=request_data
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["status"] == "success"
        assert "result" in data["outputs"]
        result_data = data["outputs"]["result"]
        assert result_data["result"] == 8

    @pytest.mark.asyncio
    async def test_execute_node_with_config(self, async_client):
        """Test node execution with configuration."""
        request_data = {
            "inputs": {
                "name": {"name": "Bob"}
            },
            "config": {
                "some_config": "value"
            }
        }
        
        response = await async_client.post(
            "/api/v1/nodes/MockGreeting/execute",
            json=request_data
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "success"

    @pytest.mark.asyncio
    async def test_execute_node_not_found(self, async_client):
        """Test executing non-existent node."""
        request_data = {
            "inputs": {}
        }
        
        response = await async_client.post(
            "/api/v1/nodes/NonExistentNode/execute",
            json=request_data
        )
        
        # The API returns 400 Bad Request when node is not found
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "detail" in data
        assert "NonExistentNode" in data["detail"]

    @pytest.mark.asyncio
    async def test_execute_node_execution_error(self, async_client):
        """Test node execution that raises an error."""
        request_data = {
            "inputs": {}
        }
        
        response = await async_client.post(
            "/api/v1/nodes/MockError/execute",
            json=request_data
        )
        
        # The API should return 400 Bad Request for execution failures
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "detail" in data
        assert "This node always fails" in data["detail"]

    @pytest.mark.asyncio
    async def test_execute_node_invalid_input(self, async_client):
        """Test node execution with invalid input format."""
        request_data = {
            "inputs": {
                "invalid_port": "some_value"
            }
        }
        
        response = await async_client.post(
            "/api/v1/nodes/MockGreeting/execute",
            json=request_data
        )
        
        # Should handle gracefully - might succeed or fail depending on node implementation
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST]

    @pytest.mark.asyncio
    async def test_execute_node_missing_required_input(self, async_client):
        """Test node execution with missing required input."""
        request_data = {
            "inputs": {}
        }
        
        response = await async_client.post(
            "/api/v1/nodes/MockGreeting/execute",
            json=request_data
        )
        
        # Should handle gracefully - might use default or fail
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST]

    @pytest.mark.asyncio
    async def test_node_list_response_structure(self, async_client):
        """Test that node list response has correct structure."""
        response = await async_client.get("/api/v1/nodes")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Verify structure
        assert isinstance(data, dict)
        assert "total" in data
        assert isinstance(data["total"], int)
        assert "nodes" in data
        assert isinstance(data["nodes"], list)
        
        # Verify each node item structure
        if len(data["nodes"]) > 0:
            node = data["nodes"][0]
            assert "node_type" in node
            assert "display_name" in node
            assert "description" in node
            assert "version" in node

    @pytest.mark.asyncio
    async def test_node_info_response_structure(self, async_client):
        """Test that node info response has correct structure."""
        response = await async_client.get("/api/v1/nodes/MockAdd")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Verify top-level structure
        assert "node_type" in data
        assert "class_name" in data
        assert "metadata" in data
        assert "input_ports" in data
        assert "output_ports" in data
        
        # Verify metadata structure
        metadata = data["metadata"]
        assert "name" in metadata
        assert "display_name" in metadata
        assert "description" in metadata
        assert "version" in metadata
        assert "author" in metadata
        
        # Verify ports are lists
        assert isinstance(data["input_ports"], list)
        assert isinstance(data["output_ports"], list)
        
        # Verify port structure if ports exist
        if len(data["input_ports"]) > 0:
            port = data["input_ports"][0]
            assert "name" in port
            assert "label" in port
            assert "schemas" in port

    @pytest.mark.asyncio
    async def test_execute_node_with_global_config_merge(self, async_client):
        """Test that node execution merges user config with GlobalConfig."""
        from deepeye.config import get_global_config
        
        # Setup: Set global config for MockConfig node
        global_config = get_global_config()
        global_config.set_node_config("MockConfig", {
            "prefix": "GlobalPrefix"
        })
        
        try:
            # Test 1: User config should override global config
            request_data = {
                "inputs": {
                    "message": {"message": "Hello"}
                },
                "config": {
                    "prefix": "UserPrefix"
                }
            }
            
            response = await async_client.post(
                "/api/v1/nodes/MockConfig/execute",
                json=request_data
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["status"] == "success"
            assert "output" in data["outputs"]
            output_data = data["outputs"]["output"]
            # User prefix should be used (overrides global)
            assert output_data["output"] == "UserPrefix: Hello"
            
            # Test 2: Without user config, global config should be used
            request_data = {
                "inputs": {
                    "message": {"message": "World"}
                }
            }
            
            response = await async_client.post(
                "/api/v1/nodes/MockConfig/execute",
                json=request_data
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["status"] == "success"
            output_data = data["outputs"]["output"]
            # Global prefix should be used
            assert output_data["output"] == "GlobalPrefix: World"
            
        finally:
            # Cleanup: Clear global config
            global_config.clear_node_config("MockConfig")


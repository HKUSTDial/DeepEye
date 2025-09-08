from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field


class BaseTool(ABC, BaseModel):
    name: str = Field(..., description="The name of the tool")
    description: str = Field(..., description="The description of the tool")
    parameters: Dict[str, Any] = Field(..., description="The parameters of the tool")

    async def __call__(self, **kwargs) -> Any:
        return await self.execute(**kwargs)
    
    @abstractmethod
    async def execute(**kwargs) -> Any:
        pass

    def to_params(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters
            }
        }


class ToolResult(BaseModel):
    output: Any = Field(..., description="The output of the tool")
    error: Optional[str] = Field(default=None, description="The error of the tool")


class ToolCollection(BaseModel):
    tools: List[BaseTool] = Field(default_factory=list, description="The tools of the tool collection")
    tool_map: Dict[str, BaseTool] = Field(default_factory=list, description="Mapping tool name to tool object")
    
    def __init__(self, tools: List[BaseTool]):
        super().__init__(tools=tools)
        self.tools = [tool for tool in tools if isinstance(tool, BaseTool)]
        self.tool_map = {
            tool.name: tool
            for tool in self.tools
        }

    def to_params(self) -> Dict[str, Any]:
        return [tool.to_params() for tool in self.tools]
    
    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> ToolResult:
        tool = self.tool_map.get(tool_name)
        if tool:
            try:
                result = await tool(**arguments)
            except Exception as e:
                return ToolResult(error=f"Error executing tool {tool_name}: {e}")
            return ToolResult(output=result)
        else:
            return ToolResult(error=f"Tool {tool_name} not found")
    
    @property
    def tool_names(self) -> List[str]:
        return [tool.name for tool in self.tools]
    
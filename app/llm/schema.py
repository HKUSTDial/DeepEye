from enum import Enum
from typing import Any, Optional, List, Literal, Union, Dict
from pydantic import BaseModel, Field
from openai.types.chat import ChatCompletionMessageFunctionToolCall


class RoleType(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class Function(BaseModel):
    name: str = Field(..., description="The name of the function")
    arguments: str = Field(..., description="The arguments of the function")
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "arguments": self.arguments
        }
    

class ToolCall(BaseModel):
    id: str = Field(..., description="The id of the tool call")
    type: str = Field(..., description="The type of the tool call")
    function: Function = Field(..., description="The function of the tool call")
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "function": self.function.to_dict()
        }


class Message(BaseModel):
    role: RoleType = Field(..., description="The role of the message")
    content: Optional[str] = Field(default=None, description="The content of the message")
    tool_calls: Optional[List[ToolCall]] = Field(default=None, description="The tool calls of the message")
    name: Optional[str] = Field(default=None, description="The name of the message")
    tool_call_id: Optional[str] = Field(default=None, description="The tool call id of the message")
    
    def __add__(self, other: Union["Message", List["Message"]]) -> List["Message"]:
        if isinstance(other, Message):
            return [self, other]
        elif isinstance(other, List):
            return [self] + other
        else:
            raise TypeError(
                f"Unsupported operand type(s) for +: '{type(self).__name__}' and '{type(other).__name__}'"
            )
    
    def __radd__(self, other: List["Message"]) -> List["Message"]:
        if isinstance(other, List):
            return other + [self]
        else:
            raise TypeError(
                f"Unsupported operand type(s) for +: '{type(other).__name__}' and '{type(self).__name__}'"
            )
    
    def to_dict(self) -> Dict[str, Any]:
        message_dict = {"role": self.role.value}
        if self.content:
            message_dict["content"] = self.content
        if self.tool_calls:
            message_dict["tool_calls"] = [tool_call.to_dict() for tool_call in self.tool_calls]
        if self.name:
            message_dict["name"] = self.name
        if self.tool_call_id:
            message_dict["tool_call_id"] = self.tool_call_id
        return message_dict
    
    @classmethod
    def system_message(cls, content: str) -> "Message":
        return cls(role=RoleType.SYSTEM, content=content)
    
    @classmethod
    def user_message(cls, content: str) -> "Message":
        return cls(role=RoleType.USER, content=content)
    
    @classmethod
    def assistant_message(cls, content: Optional[str] = None, tool_calls: Optional[List[ChatCompletionMessageFunctionToolCall]] = None) -> "Message":
        if tool_calls:
            _tool_calls = []
            for tool_call in tool_calls:
                function = Function(name=tool_call.function.name, arguments=tool_call.function.arguments)
                _tool_calls.append(ToolCall(id=tool_call.id, type=tool_call.type, function=function))
            return cls(role=RoleType.ASSISTANT, content=content, tool_calls=_tool_calls)
        else:
            return cls(role=RoleType.ASSISTANT, content=content)
    
    @classmethod
    def tool_message(cls, content: str, name: str, tool_call_id: str) -> "Message":
        return cls(role=RoleType.TOOL, content=content, name=name, tool_call_id=tool_call_id)
    

class Memory(BaseModel):
    messages: List[Message] = Field(default_factory=list, description="The messages of the memory")
    max_messages: int = Field(default=100, description="The maximum number of messages to keep in the memory")
    
    def add_message(self, message: Message) -> None:
        self.messages.append(message)
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages:]
    
    def add_messages(self, messages: List[Message]) -> None:
        self.messages.extend(messages)
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages:]
    
    def clear(self) -> None:
        self.messages.clear()
from ast import arguments
from .base import BaseAgent, AgentState
from app.tool.base import ToolCollection
from app.tool.terminate import Terminate
from app.tool.text2sql import Text2SQL
from app.tool.sqlite_database import SQLiteDatabase
from app.tool.file_system import FileSystem
from app.tool.python_execute import PythonExecute
from app.tool.text2code import Text2Code
from pydantic import Field
from typing import Literal, List, overload
import json
from app.llm.schema import ToolCall, RoleType
from app.llm.schema import Message
from app.logger import logger, create_info_box


SYSTEM_PROMPT = (
    "You are DeepEye, an all-capable AI assistant, aimed at solving any task presented by the user. You have various tools at your disposal that you can call upon to efficiently complete complex requests. Whether it's programming, information retrieval, file processing, web browsing, or human interaction (only for extreme cases), you can handle it all."
)

NEXT_STEP_PROMPT = """
Based on user needs, proactively select the most appropriate tool or combination of tools. For complex tasks, you can break down the problem and use different tools step by step to solve it. After using each tool, clearly explain the execution results and suggest the next steps.

If you want to stop the interaction at any point, use the `terminate` tool/function call.
"""

class DeepEyeAgent(BaseAgent):
    
    name: str = "DeepEye"
    description: str = "An all-capable AI assistant, aimed at solving any task presented by the user by using various tools."
    system_prompt: str = SYSTEM_PROMPT
    next_step_prompt: str = NEXT_STEP_PROMPT
    
    available_tools: ToolCollection = Field(
        default_factory=lambda: ToolCollection([
            Text2SQL(),
            SQLiteDatabase(),
            FileSystem(),
            Terminate(),
            Text2Code(),
            PythonExecute()
        ]),
        description="The available tools of the agent"
    )
    tool_choice: Literal["auto", "required"] = Field(default="auto", description="The tool choice of the agent, must be either 'auto' or 'required'")
    tool_calls: List[ToolCall] = Field(default_factory=list, description="The tool calls of the agent")
    
    async def think(self) -> bool:
        self.update_memory(RoleType.USER, self.next_step_prompt)
        try:
            response = await self.llm.ask(
                messages=self.memory.messages,
                system_message=Message.system_message(self.system_prompt),
                tools=self.available_tools.to_params(),
                tool_choice=self.tool_choice
            )
        except Exception as e:
            logger.error(f"💥 Error in think: {e}")
            self.state = AgentState.ERROR
            return False
        
        tool_calls = response.tool_calls if response.tool_calls else []
        content = response.content if response.content else ""
        
        # Create think content box
        think_info = {
            "Content": content
        }
        think_box = create_info_box(f"🧠 Agent {self.name} thinks", think_info)
        logger.info(think_box)
        logger.info(f"🔧 Agent {self.name} selected {len(tool_calls)} tools to call")
        
        if tool_calls:
            for tool_call in tool_calls:
                # Create tool call info box
                tool_info = {
                    "Function": tool_call.function.name,
                    "Arguments": tool_call.function.arguments
                }
                tool_box = create_info_box("🛠️  Tool Call Info", tool_info)
                logger.info(tool_box)
        
        self.tool_calls = tool_calls
        
        self.update_memory(RoleType.ASSISTANT, content, tool_calls=tool_calls)
        
        return bool(tool_calls)

    async def act(self) -> None:
        if not self.tool_calls:
            return self.memory.messages[-1].content or "No action needed"

        for tool_call in self.tool_calls:
            result = await self.execute_tool(tool_call)
            tool_message = Message.tool_message(
                content=result,
                name=tool_call.function.name,
                tool_call_id=tool_call.id
            )
            self.memory.add_message(tool_message)
    
    async def execute_tool(self, tool_call: ToolCall) -> str:
        tool_name = tool_call.function.name
        if tool_name not in self.available_tools.tool_names:
            logger.error(f"❌ Agent {self.name} uses unknown tool: {tool_name}")
            return "Error: Unknown tool"
        
        try:
            arguments = json.loads(tool_call.function.arguments)
            logger.info(f"⚡ Executing tool {tool_name} with arguments: {arguments}")
            result = await self.available_tools.execute_tool(tool_name, arguments)
            
            # Format tool result output
            result_info = {
                "Tool": tool_name,
                "Result": result.model_dump_json()
            }
            result_box = create_info_box("📊 Tool Result", result_info)
            logger.info(result_box)
            
            # handle terminate tool
            if tool_name == "terminate":
                logger.info(f"🏁 Terminate tool has completed the interaction")
                self.state = AgentState.FINISHED
            
            observation = f"Observation from tool `{tool_name}` execution: \n{result.model_dump_json()}"
            return observation
            
        except json.JSONDecodeError:
            logger.error(f"🔧 Error decoding tool call arguments for tool `{tool_name}`: {tool_call.function.arguments}")
            return f"Error: Invalid tool call arguments for tool `{tool_name}`"
        except Exception as e:
            logger.error(f"💥 Error executing tool `{tool_name}`: {e}")
            return f"Error: Tool `{tool_name}` encountered an error: {e}"

    async def step(self) -> None:
        should_act = await self.think()
        if should_act:
            await self.act()
            
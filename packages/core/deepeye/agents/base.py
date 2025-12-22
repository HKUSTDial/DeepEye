from typing import Annotated, Sequence, Optional, List, Dict
from typing_extensions import TypedDict
import operator

from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage
from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.prebuilt import ToolNode
from deepeye.graph.state import AgentState

class ReActAgent:
    """
    A base class for ReAct-style agents using LangGraph.
    Supports tools, streaming, and checkpointer.
    """
    def __init__(
        self, 
        model: BaseChatModel, 
        tools: List[any], 
        system_prompt: str = "",
        checkpointer: Optional[BaseCheckpointSaver] = None
    ):
        self.system_prompt = system_prompt
        self.tools = tools
        
        # Bind tools to model
        self.model = model.bind_tools(tools)
        
        # Build graph
        self.graph = self._build_graph(checkpointer)

    def _build_graph(self, checkpointer):
        workflow = StateGraph(AgentState)

        # Define nodes
        workflow.add_node("agent", self._call_model)
        workflow.add_node("tools", ToolNode(self.tools))

        # Define edges
        workflow.set_entry_point("agent")
        workflow.add_conditional_edges(
            "agent",
            self._should_continue,
            {
                "continue": "tools",
                "end": END
            }
        )
        workflow.add_edge("tools", "agent")

        return workflow.compile(checkpointer=checkpointer)

    async def _call_model(self, state: AgentState):
        messages = state["messages"]
        # Prepend system prompt if not present (simple logic)
        # In a real app, we might want to manage system message more robustly.
        if self.system_prompt:
             messages = [SystemMessage(content=self.system_prompt)] + list(messages)
             
        response = await self.model.ainvoke(messages)
        return {"messages": [response]}

    def _should_continue(self, state: AgentState):
        messages = state["messages"]
        last_message = messages[-1]
        if last_message.tool_calls:
            return "continue"
        return "end"

    async def ainvoke(self, input_message: str, thread_id: str = None, config: dict = None):
        """
        Run the agent with a single input message.
        """
        run_config = {"configurable": {"thread_id": thread_id}} if thread_id else {}
        if config:
            run_config.update(config)
            
        final_state = await self.graph.ainvoke(
            {"messages": [HumanMessage(content=input_message)]},
            config=run_config
        )
        return final_state

    async def astream(self, input_message: str, thread_id: str = None, config: dict = None):
        """
        Async generator to stream events from the graph.
        """
        run_config = {"configurable": {"thread_id": thread_id}} if thread_id else {}
        if config:
            run_config.update(config)
        
        async for event in self.graph.astream_events(
            {"messages": [HumanMessage(content=input_message)]}, 
            config=run_config,
            version="v2"
        ):
            yield event


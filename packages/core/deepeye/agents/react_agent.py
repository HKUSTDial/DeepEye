from typing import Any, AsyncIterator

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode

from deepeye.agents.base import BaseAgent
from deepeye.graph.state import AgentState


DEFAULT_MAX_STEPS = 50
# Max messages to send to the model (older messages dropped to avoid context_length_exceeded)
DEFAULT_MAX_CONTEXT_MESSAGES = 20


class ReActAgent(BaseAgent):
    """ReAct-style agent using LangGraph. Callbacks propagate to all nodes."""

    def __init__(
        self,
        model: BaseChatModel,
        tools: list[Any],
        system_prompt: str = "",
        checkpointer: BaseCheckpointSaver | None = None,
        max_steps: int = DEFAULT_MAX_STEPS,
        max_context_messages: int = DEFAULT_MAX_CONTEXT_MESSAGES,
    ):
        self._bound_model = model.bind_tools(tools)
        self.max_steps = max_steps
        self.max_context_messages = max_context_messages
        super().__init__(model, tools, system_prompt, checkpointer)

    def _build_graph(self) -> Any:
        workflow = StateGraph(AgentState)
        workflow.add_node("agent", self._call_model)
        workflow.add_node("tools", ToolNode(self.tools))
        workflow.set_entry_point("agent")
        workflow.add_conditional_edges("agent", self._should_continue, {"continue": "tools", "end": END})
        workflow.add_edge("tools", "agent")
        return workflow.compile(checkpointer=self.checkpointer)

    async def _call_model(self, state: AgentState, config: RunnableConfig) -> dict:
        """Model node - callbacks from config are automatically used."""
        messages = state["messages"]
        if self.max_context_messages and len(messages) > self.max_context_messages:
            messages = list(messages)[-self.max_context_messages:]
        # OpenAI API requires: every AIMessage with tool_calls must be followed by ToolMessage(s).
        # If we truncated and the last message is an AIMessage with tool_calls (without its ToolMessages), drop it to avoid 400.
        while messages and isinstance(messages[-1], AIMessage) and getattr(messages[-1], "tool_calls", None):
            messages = list(messages)[:-1]
        if not messages:
            fallback = list(state["messages"])
            while fallback and isinstance(fallback[-1], AIMessage) and getattr(fallback[-1], "tool_calls", None):
                fallback = fallback[:-1]
            messages = fallback[-1:] if fallback else list(state["messages"])[-1:]
        if self.system_prompt:
            messages = [SystemMessage(content=self.system_prompt)] + list(messages)
        response = await self._bound_model.ainvoke(messages, config=config)
        return {"messages": [response]}

    async def _should_continue(self, state: AgentState) -> str:
        last_message = state["messages"][-1]
        return "continue" if last_message.tool_calls else "end"

    async def ainvoke(self, input_message: str, thread_id: str | None = None, config: dict | None = None) -> dict:
        run_config: dict = {"configurable": {"thread_id": thread_id}} if thread_id else {"configurable": {}}
        run_config["recursion_limit"] = self.max_steps
        if config:
            # Deep merge configurable to preserve thread_id
            if "configurable" in config:
                run_config["configurable"].update(config["configurable"])
                config = {k: v for k, v in config.items() if k != "configurable"}
            run_config.update(config)
        return await self.graph.ainvoke({"messages": [HumanMessage(content=input_message)]}, config=run_config)

    async def astream(self, input_message: str, thread_id: str | None = None, config: dict | None = None) -> AsyncIterator[Any]:
        run_config: dict = {"configurable": {"thread_id": thread_id}} if thread_id else {"configurable": {}}
        run_config["recursion_limit"] = self.max_steps
        if config:
            # Deep merge configurable to preserve thread_id
            if "configurable" in config:
                run_config["configurable"].update(config["configurable"])
                config = {k: v for k, v in config.items() if k != "configurable"}
            run_config.update(config)
        async for event in self.graph.astream_events({"messages": [HumanMessage(content=input_message)]}, config=run_config, version="v2"):
            yield event

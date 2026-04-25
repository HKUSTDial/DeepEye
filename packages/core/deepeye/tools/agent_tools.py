"""Sub-agent tool factories.

These create tools that wrap sub-agents (SQLAgent, CodeAgent).
Events from sub-agents are captured by the callback system and persisted
alongside supervisor events, enabling unified history reconstruction.
"""

from typing import Any, Callable

from langchain_core.language_models import BaseChatModel

from deepeye.sandbox import SandboxProtocol
from deepeye.tools.base import tool


def create_sql_agent_tool(
    db_uri: str, 
    model: BaseChatModel, 
    session_id: str,
    sandbox: SandboxProtocol | None = None,
    on_files_changed: Callable[[], None] | None = None,
    callbacks: list[Any] | None = None
) -> Callable:
    """Factory that creates a Tool wrapping a SQLAgent.
    
    Args:
        db_uri: Database connection string
        model: LLM model
        session_id: Session ID for maintaining conversation context
        sandbox: Sandbox instance for writing query results
        on_files_changed: Callback when files are written to sandbox
        callbacks: Callbacks for event tracking
    """
    from deepeye.agents.sql_agent import SQLAgent
    import asyncio
    
    # Create write_to_workspace callback if sandbox provided
    write_to_workspace = None
    if sandbox:
        def write_to_workspace(filename: str, content: str) -> str:
            """Write file to sandbox /workspace directory (sync wrapper for async exec)."""
            filepath = f"/workspace/{filename}"
            command = f"cat > {filepath} << 'EOFCSV'\n{content}\nEOFCSV"
            
            # Execute command in sandbox (handle sync/async context)
            try:
                loop = asyncio.get_running_loop()
                # We're in an async context, schedule and wait
                future = asyncio.run_coroutine_threadsafe(
                    sandbox.exec_command(command), loop
                )
                future.result(timeout=30)
            except RuntimeError:
                # No running loop, create new one
                asyncio.run(sandbox.exec_command(command))
            
            # Notify frontend about file changes
            if on_files_changed:
                try:
                    loop = asyncio.get_running_loop()
                    loop.call_soon(on_files_changed)
                except RuntimeError:
                    on_files_changed()
            
            return filepath

    sql_agent = SQLAgent(model=model, database=db_uri, write_to_workspace=write_to_workspace)
    # Use session-based thread_id to maintain context across calls
    sub_thread_id = f"sql_agent_{session_id}"

    @tool
    async def ask_database(question: str) -> str:
        """
        Use this tool to answer questions about data in the database.
        Input should be a natural language question.
        Query results will be saved to /workspace as CSV files.
        """
        result = await sql_agent.ainvoke(
            question,
            thread_id=sub_thread_id,
            config={"tags": ["sub_agent"], "callbacks": callbacks},
        )

        messages = result.get("messages", [])
        return messages[-1].content if messages else ""

    return ask_database


def create_code_agent_tool(
    sandbox_tools: list, 
    model: BaseChatModel, 
    session_id: str,
    callbacks: list[Any] | None = None
) -> Callable:
    """
    Factory that creates a Tool wrapping a CodeAgent.
    
    Args:
        sandbox_tools: Tool callables supplied by the application runtime
        model: LLM model
        session_id: Session ID for maintaining conversation context across calls
        callbacks: Callbacks for event tracking
        
    Returns:
        analyze_data tool function
        
    Example:
        sandbox = await runtime.create_sandbox(session_id)
        tools = runtime.create_sandbox_tools(sandbox)
        analyze_data = create_code_agent_tool(tools, model, session_id)
    """
    from deepeye.agents.code_agent import CodeAgent

    code_agent = CodeAgent(model=model, tools=sandbox_tools)
    # Use session-based thread_id to maintain context across calls
    sub_thread_id = f"code_agent_{session_id}"

    @tool
    async def analyze_data(question: str) -> str:
        """
        Perform data analysis or visualization using Python in sandbox.

        Args:
            question: Analysis task (e.g. "Plot the sales trend")
        
        Returns:
            Analysis result or error message
            
        Note:
            The code agent maintains context across calls within the same session.
            It remembers previously created files and executed commands.
        """
        # Run code agent with persistent thread_id
        result = await code_agent.ainvoke(
            question,
            thread_id=sub_thread_id,
            config={"tags": ["sub_agent"], "callbacks": callbacks},
        )

        messages = result.get("messages", [])
        return messages[-1].content if messages else ""

    return analyze_data


def create_workflow_agent_tool(
    model: BaseChatModel,
    session_id: str,
    callbacks: list[Any] | None = None,
    system_prompt: str | None = None,
) -> Callable:
    """
    Factory that creates a Tool wrapping a WorkflowAgent.

    Args:
        model: LLM model
        session_id: Session ID for maintaining conversation context across calls
        callbacks: Callbacks for event tracking

    Returns:
        design_workflow tool function
    """
    from deepeye.agents.workflow_agent import WorkflowAgent
    from deepeye.tools.planning_tools import create_plan, mark_step_done, update_plan

    workflow_agent = WorkflowAgent(
        model=model,
        system_prompt=system_prompt,
        tools=[create_plan, update_plan, mark_step_done],
    )
    sub_thread_id = f"workflow_agent_{session_id}"

    @tool
    async def design_workflow(goal: str) -> str:
        """
        Design a workflow JSON for a data analysis goal.

        Args:
            goal: The analysis objective in natural language.
        """
        result = await workflow_agent.ainvoke(
            goal,
            thread_id=sub_thread_id,
            config={"tags": ["sub_agent"], "callbacks": callbacks},
        )

        messages = result.get("messages", [])
        return messages[-1].content if messages else ""

    return design_workflow

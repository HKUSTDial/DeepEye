from typing import Callable

from langchain_community.utilities import SQLDatabase
from langchain_core.language_models import BaseChatModel
from langgraph.checkpoint.base import BaseCheckpointSaver

from deepeye.agents.react_agent import ReActAgent
from deepeye.tools.database import create_database_tools

SQL_AGENT_SYSTEM_PROMPT = """You are an expert Data Detective and SQL Analyst.
Your goal is to answer user questions by querying the database.

Target Database: {dialect}

Guidelines:
1. Always start by listing tables to understand the database structure if you don't know it.
2. Check the schema of relevant tables before writing SQL.
3. Write standard SQL queries compatible with {dialect}.
4. If a query fails, analyze the error message and try to correct the query.
5. Do not make DML statements (INSERT, UPDATE, DELETE) unless explicitly asked.
6. IMPORTANT: If the tool output contains a file path (e.g., 'Full result saved to: /workspace/...'), YOU MUST explicitly state this file path in your final answer so the user or other agents can use it.

Answer the user's question concisely based on the data retrieved.
"""


class SQLAgent(ReActAgent):
    """A specialized agent for SQL database interaction."""

    def __init__(
        self,
        model: BaseChatModel,
        database: SQLDatabase | str,
        write_to_workspace: Callable[[str, str], str] | None = None,
        checkpointer: BaseCheckpointSaver | None = None,
        system_prompt: str = SQL_AGENT_SYSTEM_PROMPT,
        max_steps: int = 50,
    ):
        """
        Initialize SQL Agent.
        
        Args:
            model: LLM model
            database: Database connection string or SQLDatabase instance
            write_to_workspace: Callback to write files to sandbox workspace
                               Signature: (filename, content) -> filepath
            checkpointer: LangGraph checkpointer for state persistence
            system_prompt: System prompt template
            max_steps: Maximum execution steps
        """
        self.db = SQLDatabase.from_uri(database) if isinstance(database, str) else database
        db_tools = create_database_tools(self.db, write_to_workspace)
        formatted_prompt = system_prompt.format(dialect=self.db.dialect)

        super().__init__(
            model=model,
            tools=db_tools,
            system_prompt=formatted_prompt,
            checkpointer=checkpointer,
            max_steps=max_steps,
        )


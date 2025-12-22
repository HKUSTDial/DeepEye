from typing import Optional, Union
from langchain_core.language_models import BaseChatModel
from langchain_community.utilities import SQLDatabase

from deepeye.agents.base import ReActAgent
from deepeye.tools.database import get_database_tools

SQL_AGENT_SYSTEM_PROMPT = """You are an expert Data Detective and SQL Analyst.
Your goal is to answer user questions by querying the database.

Target Database: {dialect}

Guidelines:
1. Always start by listing tables to understand the database structure if you don't know it.
2. Check the schema of relevant tables before writing SQL.
3. Write standard SQL queries compatible with {dialect}.
4. If a query fails, analyze the error message and try to correct the query.
5. Do not make DML statements (INSERT, UPDATE, DELETE) unless explicitly asked.
6. IMPORTANT: If the tool output contains a file path (e.g., 'Full result saved to: ...'), YOU MUST explicitly state this file path in your final answer so the user or other agents can use it.

Answer the user's question concisely based on the data retrieved.
"""

class SQLAgent(ReActAgent):
    """
    A specialized agent for SQL database interaction.
    It automatically configures database tools and system prompts.
    """

    def __init__(
        self,
        model: BaseChatModel,
        database: Union[SQLDatabase, str],
        checkpointer: Optional[any] = None,
        system_prompt: str = SQL_AGENT_SYSTEM_PROMPT
    ):
        """
        Initialize the SQL Agent.
        
        Args:
            model: The LLM to use.
            database: A SQLDatabase instance or a connection string URI.
            checkpointer: Optional memory checkpointer.
            system_prompt: Custom system prompt template. Must contain {dialect} placeholder 
                           if you want dynamic dialect injection.
        """
        # Handle connection string or instance
        if isinstance(database, str):
            self.db = SQLDatabase.from_uri(database)
        else:
            self.db = database

        # Initialize tools bound to this database
        db_tools = get_database_tools(self.db)
        
        # Inject dialect into system prompt
        formatted_system_prompt = system_prompt.format(dialect=self.db.dialect)
        
        super().__init__(
            model=model,
            tools=db_tools,
            checkpointer=checkpointer,
            system_prompt=formatted_system_prompt
        )


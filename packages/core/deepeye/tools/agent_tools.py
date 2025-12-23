"""Sub-agent tool factories.

These create tools that wrap sub-agents (SQLAgent, CodeAgent).
Events from sub-agents are captured by the callback system and persisted
alongside supervisor events, enabling unified history reconstruction.
"""

import os
import shutil
import uuid
from typing import Any, Callable

from langchain_core.language_models import BaseChatModel

from deepeye.tools.base import tool


def create_sql_agent_tool(db_uri: str, model: BaseChatModel, callbacks: list[Any] | None = None) -> Callable:
    """Factory that creates a Tool wrapping a SQLAgent."""
    from deepeye.agents.sql_agent import SQLAgent

    sql_agent = SQLAgent(model=model, database=db_uri)

    @tool
    async def ask_database(question: str) -> str:
        """
        Use this tool to answer questions about data in the database.
        Input should be a natural language question.
        """
        sub_thread_id = f"sub_sql_{uuid.uuid4()}"

        result = await sql_agent.ainvoke(
            question,
            thread_id=sub_thread_id,
            config={"tags": ["sub_agent"], "callbacks": callbacks},
        )

        messages = result.get("messages", [])
        return messages[-1].content if messages else ""

    return ask_database


def create_code_agent_tool(sandbox_url: str, model: BaseChatModel, callbacks: list[Any] | None = None) -> Callable:
    """Factory that creates a Tool wrapping a CodeAgent."""
    from deepeye.agents.code_agent import CodeAgent

    code_agent = CodeAgent(model=model, sandbox_url=sandbox_url)

    @tool
    async def analyze_data(question: str, file_paths: list[str]) -> str:
        """
        Use this tool to perform advanced data analysis or visualization using Python.

        Args:
            question: The analysis task description (e.g. "Plot the sales trend").
            file_paths: A list of local file paths (e.g. ["artifacts/data.csv"]) that contain the data to analyze.
                        These files will be mounted into the secure sandbox environment.
        """
        sub_thread_id = f"sub_code_{uuid.uuid4()}"

        # Prepare Files (mount to sandbox)
        host_artifacts_dir = os.path.abspath("artifacts")
        os.makedirs(host_artifacts_dir, exist_ok=True)

        mounted_info = []
        for host_path in file_paths:
            if not os.path.exists(host_path):
                return f"Error: File not found at {host_path}"

            filename = os.path.basename(host_path)
            abs_host_path = os.path.abspath(host_path)
            if not abs_host_path.startswith(host_artifacts_dir):
                dest_path = os.path.join(host_artifacts_dir, filename)
                shutil.copy2(host_path, dest_path)

            mounted_info.append(f"- {filename} is available at /mnt/data/{filename}")

        # Augment prompt with file info
        augmented_question = question
        if mounted_info:
            augmented_question += "\n[System: The following files have been mounted for your analysis:]\n" + "\n".join(mounted_info)

        result = await code_agent.ainvoke(
            augmented_question,
            thread_id=sub_thread_id,
            config={"tags": ["sub_agent"], "callbacks": callbacks},
        )

        messages = result.get("messages", [])
        return messages[-1].content if messages else ""

    return analyze_data

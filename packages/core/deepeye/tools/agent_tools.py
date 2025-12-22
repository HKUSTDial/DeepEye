from typing import Callable, List, Any
from langchain_core.language_models import BaseChatModel
from deepeye.agents.sql_agent import SQLAgent
from deepeye.agents.code_agent import CodeAgent
from deepeye.tools.base import tool
import os
import uuid

def create_sql_agent_tool(db_uri: str, model: BaseChatModel, callbacks: List[Any] = None) -> Callable:
    """
    Factory that creates a Tool wrapping a SQLAgent.
    """
    sql_agent = SQLAgent(model=model, database=db_uri)
    
    @tool
    async def ask_database(question: str) -> str:
        """
        Use this tool to answer questions about data in the database.
        Input should be a natural language question.
        """
        sub_thread_id = f"sub_sql_{uuid.uuid4()}"
        
        # Tag the run for logger
        result = await sql_agent.ainvoke(
            question, 
            thread_id=sub_thread_id,
            config={
                "tags": ["sub_agent"],
                "callbacks": callbacks # Inject callbacks here
            }
        )
        
        return result["messages"][-1].content
        
    return ask_database

def create_code_agent_tool(sandbox_url: str, model: BaseChatModel, callbacks: List[Any] = None) -> Callable:
    """
    Factory that creates a Tool wrapping a CodeAgent (Python Sandbox).
    """
    code_agent = CodeAgent(model=model, sandbox_url=sandbox_url)
    
    @tool
    async def analyze_data(question: str, file_paths: List[str]) -> str:
        """
        Use this tool to perform advanced data analysis or visualization using Python.
        
        Args:
            question: The analysis task description (e.g. "Plot the sales trend").
            file_paths: A list of local file paths (e.g. ["artifacts/data.csv"]) that contain the data to analyze.
                        These files will be mounted into the secure sandbox environment.
        """
        sub_thread_id = f"sub_code_{uuid.uuid4()}"
        
        # 1. Prepare Files (Map to /mnt/data via Bind Mount)
        # The sandbox mounts host's ./artifacts/ to container's /mnt/data/
        host_artifacts_dir = os.path.abspath("artifacts")
        os.makedirs(host_artifacts_dir, exist_ok=True)
        
        mounted_info = []
        for host_path in file_paths:
            if not os.path.exists(host_path):
                return f"Error: File not found at {host_path}"
            
            filename = os.path.basename(host_path)
            
            # Check if file is already in artifacts dir
            abs_host_path = os.path.abspath(host_path)
            if abs_host_path.startswith(host_artifacts_dir):
                # It's already in the mounted directory
                container_path = f"/mnt/data/{filename}"
            else:
                # Copy to artifacts dir
                import shutil
                dest_path = os.path.join(host_artifacts_dir, filename)
                shutil.copy2(host_path, dest_path)
                container_path = f"/mnt/data/{filename}"
                
            mounted_info.append(f"- {filename} is available at {container_path}")
        
        # 2. Augment Prompt with File Info
        if mounted_info:
            system_note = "\n[System: The following files have been mounted for your analysis:]\n" + "\n".join(mounted_info)
            augmented_question = question + system_note
        else:
            augmented_question = question

        # 3. Run Sub-Agent
        result = await code_agent.ainvoke(
            augmented_question,
            thread_id=sub_thread_id,
            config={
                "tags": ["sub_agent"],
                "callbacks": callbacks # Inject callbacks here
            }
        )
        
        return result["messages"][-1].content
        
    return analyze_data

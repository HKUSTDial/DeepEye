"""Sandbox tools for agent use"""

from typing import Callable

from deepeye.tools.base import tool
from app.sandbox.docker_sandbox import DockerSandbox
from app.schemas import SandboxEvent, SandboxEventType


def create_bash_tool(
    sandbox: DockerSandbox,
    on_files_changed: Callable[[], None] | None = None
):
    """
    Create bash tool for executing commands in sandbox.
    
    Args:
        sandbox: Created sandbox instance
        on_files_changed: Callback to notify when files may have changed
        
    Returns:
        Bash tool function
    """
    
    @tool
    async def bash(command: str) -> str:
        """
        Execute bash command in the sandbox.
        
        The sandbox is a Linux environment with pre-installed tools:
        - Python 3.11 with pandas, numpy, matplotlib, seaborn, scipy, sklearn
        - Standard Unix tools (ls, cat, mkdir, etc.)
        - Working directory: /workspace
        
        Use this to:
        - Run Python scripts
        - Install packages (pip install)
        - File operations (cat, echo, ls, mkdir, etc.)
        - Data processing and analysis
        
        Args:
            command: Bash command to execute
            
        Returns:
            Command output (stdout) or error message
            
        Examples:
            - "python script.py"
            - "pip install requests"
            - "cat data.csv | head -10"
            - "echo 'print(1+1)' > script.py && python script.py"
        """
        try:
            result = await sandbox.exec_command(command)
            
            if result.success:
                # Notify files may have changed
                if on_files_changed:
                    on_files_changed()
                return result.stdout or "(Command completed successfully)"
            else:
                return f"Error (exit code {result.exit_code}):\n{result.stderr}"
                
        except Exception as e:
            return f"Execution failed: {str(e)}"
    
    return bash


def get_sandbox_tools(
    sandbox: DockerSandbox,
    on_files_changed: Callable[[], None] | None = None
) -> list:
    """
    Get all tools for sandbox.
    
    Args:
        sandbox: Created sandbox instance
        on_files_changed: Callback to notify when files may have changed
        
    Returns:
        List of tool functions
    """
    return [create_bash_tool(sandbox, on_files_changed)]


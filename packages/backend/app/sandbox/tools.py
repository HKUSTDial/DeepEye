"""Sandbox tools for agent use"""

import re
from typing import Callable

from deepeye.tools.base import tool
from app.sandbox.docker_sandbox import DockerSandbox

_MUTATING_COMMAND_PATTERNS = (
    re.compile(r"(^|[;&|]\s*)(mkdir|rmdir|rm|mv|cp|touch|install|ln|unlink|truncate|chmod|chown)\b"),
    re.compile(r"(^|[;&|]\s*)(sed\s+-i|perl\s+-pi|tee)\b"),
    re.compile(r"(^|[;&|]\s*)(tar\s+[^;\n]*\s-[^;\n]*[cuxr]|unzip|zip)\b"),
    re.compile(r"(^|[;&|]\s*)(git\s+(apply|am|checkout|restore|clean|stash|commit|merge|rebase|cherry-pick))\b"),
    re.compile(r"(^|[;&|]\s*)(python|python3|node|bash|sh)\b[^;\n]*\s-c\b"),
    re.compile(r"(^|[;&|]\s*)(echo|printf|cat)\b[^;\n]*[>]{1,2}"),
    re.compile(r"(^|[;&|]\s*)[^#\n]*\s[>]{1,2}\s*[^>\n]"),
)


def _command_may_modify_files(command: str) -> bool:
    normalized = command.strip()
    if not normalized:
        return False
    return any(pattern.search(normalized) for pattern in _MUTATING_COMMAND_PATTERNS)


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
                # Only notify on commands that are likely to mutate workspace files.
                if on_files_changed and _command_may_modify_files(command):
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

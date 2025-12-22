import requests
import os
import time
from typing import List, Callable
from deepeye.tools.base import tool
from functools import partial

def create_sandbox_tool(sandbox_url: str) -> Callable:
    @tool
    def run_python_in_sandbox(code: str) -> str:
        """
        Executes Python code in a secure, persistent Docker sandbox.
        Use this to perform calculations, data analysis, or plotting.
        Pre-installed libraries: pandas, numpy, matplotlib, seaborn, etc.
        Files are available at /mnt/data (or mounted paths).
        
        Returns text output (stdout) combined with any error messages.
        """
        try:
            response = requests.post(
                f"{sandbox_url}/execute",
                json={"code": code},
                timeout=30 # 30 seconds timeout
            )
            
            if response.status_code != 200:
                return f"Sandbox System Error ({response.status_code}): {response.text}"
                
            result = response.json()
            
            output = result.get("output", "")
            error = result.get("error")
            # Images are saved to filesystem by agent code, no need to handle here
            
            # Combine output
            full_output = ""
            if output:
                full_output += f"{output}\n"
            if error:
                full_output += f"\nERROR:\n{error}\n"
                
            if not full_output.strip():
                return "[Code executed successfully with no output]"
                
            return full_output.strip()
            
        except requests.exceptions.RequestException as e:
            return f"Connection Error to Sandbox: {str(e)}"
        except Exception as e:
            return f"System Error: {str(e)}"

    return run_python_in_sandbox

def get_sandbox_tools(sandbox_url: str | None = None) -> list:
    url = sandbox_url or os.getenv("SANDBOX_URL", "http://code-sandbox:8000")
    return [create_sandbox_tool(url)]

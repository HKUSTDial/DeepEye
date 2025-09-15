from .base import BaseTool
import subprocess
import tempfile
import os
from pydantic import model_validator
from app.logger import logger


class PythonExecute(BaseTool):
    name: str = "python_execute"
    description: str = "Execute existing Python code safely and return the output. Use this only when you have specific Python code that needs to be run."
    parameters: dict = {
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": "The Python code to execute.",
            }
        },
        "required": ["code"],
    }
    
    timeout: int = 30  # Default timeout in seconds
    
    @model_validator(mode="after")
    def _initialize_python_execute(self) -> "PythonExecute":
        """Initialize the PythonExecute tool."""
        return self

    async def execute(self, code: str):
        """Execute the Python code and return the result."""
        try:
            # Create a temporary file for the code
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(code)
                temp_file = f.name
            
            try:
                # Execute the code with timeout
                result = subprocess.run(
                    ['python', temp_file],
                    capture_output=True,
                    text=True,
                    timeout=self.timeout
                )
                
                return {
                    "success": result.returncode == 0,
                    "output": result.stdout,
                    "error": result.stderr,
                    "return_code": result.returncode
                }
                
            finally:
                # Clean up temporary file
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
                    
        except subprocess.TimeoutExpired:
            logger.warning(f"Python code execution timed out after {self.timeout} seconds")
            return {
                "success": False,
                "output": "",
                "error": f"Code execution timed out after {self.timeout} seconds",
                "return_code": -1
            }
        except Exception as e:
            logger.error(f"Error executing Python code: {e}")
            return {
                "success": False,
                "output": "",
                "error": f"Execution error: {str(e)}",
                "return_code": -1
            }


if __name__ == "__main__":
    import asyncio
    
    async def test_python_execute():
        """Test the PythonExecute tool with sample code."""
        python_execute = PythonExecute()
        
        # Test cases
        test_cases = [
            "print('Hello, World!')",
            "import math\nprint(f'Pi is approximately {math.pi:.2f}')",
            "def factorial(n):\n    return 1 if n <= 1 else n * factorial(n-1)\nprint(factorial(5))",
            "print(1/0)"  # This should cause an error
        ]
        
        for i, code in enumerate(test_cases, 1):
            print(f"\n--- Test Case {i} ---")
            print(f"Code:\n{code}")
            
            result = await python_execute.execute(code)
            print(f"Success: {result['success']}")
            print(f"Output: {result['output']}")
            if result['error']:
                print(f"Error: {result['error']}")
            print(f"Return Code: {result['return_code']}")
    
    # Run the test
    asyncio.run(test_python_execute())
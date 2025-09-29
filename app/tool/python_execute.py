from .base import BaseTool
import subprocess
import tempfile
import os
import shutil
import re
import sys
import json
from pathlib import Path
from pydantic import model_validator
from app.logger import logger


class PythonExecute(BaseTool):
    name: str = "python_execute"
    description: str = """
    Execute existing Python code safely and return the output. 
    Use this when you have specific Python code that needs to be run.
    Install missing packages based on error messages.
    """
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
    use_temp_venv: bool = True  # Whether to create temporary virtual environment
    
    # Package mapping for common import names to pip package names
    package_mapping: dict = {
        "cv2": "opencv-python",
        "PIL": "Pillow", 
        "sklearn": "scikit-learn",
        "yaml": "pyyaml",
        "dateutil": "python-dateutil",
        "bs4": "beautifulsoup4",
        "requests": "requests",
        "pandas": "pandas",
        "numpy": "numpy", 
        "matplotlib": "matplotlib",
        "seaborn": "seaborn",
        "plotly": "plotly",
        "scipy": "scipy"
    }
    
    # Cache for reusing virtual environments
    _venv_cache: dict = {}
    
    @model_validator(mode="after")
    def _initialize_python_execute(self) -> "PythonExecute":
        """Initialize the PythonExecute tool."""
        return self

    
    def _detect_missing_packages(self, error_output: str) -> list:
        """Detect missing packages from error output and map to correct pip package names."""
        missing_packages = []
        
        # Common error patterns for missing packages
        patterns = [
            r"ModuleNotFoundError: No module named '(\w+)'",
            r"ImportError: No module named '(\w+)'",
            r"ModuleNotFoundError: No module named \"(\w+)\"",
            r"ImportError: No module named \"(\w+)\"",
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, error_output)
            for match in matches:
                # Map import name to pip package name
                pip_package = self.package_mapping.get(match, match)
                if pip_package not in missing_packages:
                    missing_packages.append(pip_package)
        
        return missing_packages
    
    def _install_packages_to_venv(self, venv_path: str, packages: list) -> bool:
        """Install packages to an existing virtual environment."""
        try:
            # Get pip executable path
            if os.name == 'nt':  # Windows
                pip_exe = os.path.join(venv_path, "Scripts", "pip.exe")
            else:  # Unix/Linux
                pip_exe = os.path.join(venv_path, "bin", "pip")
            
            # Install packages
            for package in packages:
                try:
                    logger.info(f"Installing missing package: {package}")
                    subprocess.run([
                        pip_exe, "install", package, "--quiet", "--no-warn-script-location"
                    ], check=True, capture_output=True, timeout=60)
                    logger.info(f"Successfully installed {package}")
                except subprocess.CalledProcessError as e:
                    logger.warning(f"Failed to install {package}: {e}")
                    return False
                except subprocess.TimeoutExpired:
                    logger.warning(f"Timeout installing {package}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error installing packages: {e}")
            return False
    
    def _create_temp_venv(self) -> tuple[str, str]:
        """Create a clean temporary virtual environment (no packages pre-installed)."""
        # Create temporary directory for venv
        temp_dir = tempfile.mkdtemp(prefix="python_execute_venv_")
        venv_path = os.path.join(temp_dir, "venv")
        
        try:
            # Create virtual environment
            logger.info(f"Creating clean virtual environment at {venv_path}")
            subprocess.run([
                sys.executable, "-m", "venv", venv_path
            ], check=True, capture_output=True)
            
            # Get Python executable path
            if os.name == 'nt':  # Windows
                python_exe = os.path.join(venv_path, "Scripts", "python.exe")
            else:  # Unix/Linux
                python_exe = os.path.join(venv_path, "bin", "python")
            
            logger.info("Clean virtual environment created successfully")
            return python_exe, temp_dir
            
        except Exception as e:
            # Clean up on failure
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
            raise e
    
    def _cleanup_temp_venv(self, temp_dir: str):
        """Clean up temporary virtual environment directory."""
        try:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
                logger.info(f"Cleaned up temporary virtual environment: {temp_dir}")
        except Exception as e:
            logger.warning(f"Failed to clean up temporary directory {temp_dir}: {e}")
    
    def _get_python_executable(self, code: str = None) -> tuple[str, str]:
        """Get the appropriate Python executable path."""
        if self.use_temp_venv:
            # Use a simple cache key for clean venv (no packages)
            cache_key = "clean_venv"
            
            # Check if we have a cached clean venv
            if cache_key in self._venv_cache:
                cached_info = self._venv_cache[cache_key]
                if os.path.exists(cached_info['python_exe']):
                    logger.info(f"Reusing cached clean virtual environment")
                    return cached_info['python_exe'], cached_info['temp_dir']
                else:
                    # Remove invalid cache entry
                    del self._venv_cache[cache_key]
            
            # Create new clean virtual environment
            logger.info("Creating new clean virtual environment")
            python_exe, temp_dir = self._create_temp_venv()
            
            # Cache the environment info
            self._venv_cache[cache_key] = {
                'python_exe': python_exe,
                'temp_dir': temp_dir
            }
            
            return python_exe, temp_dir
        else:
            # Use system Python
            return "python", None

    async def execute_code(self, code: str) -> dict:
        """Execute Python code in virtual environment (basic execution without auto-install)."""
        temp_file = None
        temp_dir = None
        
        try:
            # Create a temporary file for the code
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(code)
                temp_file = f.name
            
            # Get the appropriate Python executable and temp directory
            python_executable, temp_dir = self._get_python_executable(code)
            
            # Set working directory to DeepEye root for consistent file operations
            current_dir = Path(__file__).parent.parent.parent  # Go up to DeepEye root
            workspace_dir = current_dir / "workspace"
            
            # Ensure workspace directory exists
            workspace_dir.mkdir(exist_ok=True)
            
            # Execute the code
            result = subprocess.run(
                [python_executable, temp_file],
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=str(current_dir)  # Set working directory to DeepEye root
            )
            
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr,
                "return_code": result.returncode,
                "venv_path": os.path.join(temp_dir, "venv") if temp_dir and self.use_temp_venv else None
            }
                           
        except subprocess.TimeoutExpired:
            logger.warning(f"Python code execution timed out after {self.timeout} seconds")
            return {
                "success": False,
                "output": "",
                "error": f"Code execution timed out after {self.timeout} seconds",
                "return_code": -1,
                "venv_path": None
            }
        except Exception as e:
            logger.error(f"Error executing Python code: {e}")
            return {
                "success": False,
                "output": "",
                "error": f"Execution error: {str(e)}",
                "return_code": -1,
                "venv_path": None
            }
        finally:
            # Clean up temporary file
            if temp_file and os.path.exists(temp_file):
                os.unlink(temp_file)
    
    async def install_packages(self, error_output: str, venv_path: str = None) -> dict:
        """Install missing packages based on error output."""
        if not venv_path:
            return {
                "success": False,
                "message": "No virtual environment path provided",
                "packages_installed": []
            }
        
        if not os.path.exists(venv_path):
            return {
                "success": False,
                "message": f"Virtual environment not found: {venv_path}",
                "packages_installed": []
            }
        
        # Detect missing packages from error output
        missing_packages = self._detect_missing_packages(error_output)
        
        if not missing_packages:
            return {
                "success": True,
                "message": "No missing packages detected",
                "packages_installed": []
            }
        
        # Install the packages
        logger.info(f"Installing missing packages: {missing_packages}")
        success = self._install_packages_to_venv(venv_path, missing_packages)
        
        return {
            "success": success,
            "message": f"{'Successfully' if success else 'Failed to'} install packages: {missing_packages}",
            "packages_installed": missing_packages if success else []
        }
    
    async def execute(self, code: str, auto_install: bool = True, max_retries: int = 1) -> dict:
        """
        Execute Python code with optional automatic package installation.
        
        Args:
            code: Python code to execute
            auto_install: Whether to automatically install missing packages
            max_retries: Maximum number of retries after installing packages
            
        Returns:
            Dict with execution results
        """
        # First attempt: execute code
        result = await self.execute_code(code)
        
        # If successful or auto_install is disabled, return immediately
        if result["success"] or not auto_install:
            return result
        
        # If failed and auto_install is enabled, try to install missing packages
        for attempt in range(max_retries):
            if result["venv_path"]:
                # Try to install missing packages
                install_result = await self.install_packages(result["error"], result["venv_path"])
                
                if install_result["success"] and install_result["packages_installed"]:
                    logger.info(f"Installed packages: {install_result['packages_installed']}, retrying execution...")
                    # Retry execution
                    result = await self.execute_code(code)
                    
                    if result["success"]:
                        # Add installation info to result
                        result["packages_installed"] = install_result["packages_installed"]
                        return result
                else:
                    # No packages were installed, break the retry loop
                    break
            else:
                # No virtual environment available for package installation
                break
        
        # If we get here, execution failed even after trying to install packages
        return result


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
from typing import Callable, Optional, Type, Any
from langchain_core.tools import tool as lc_tool
from langchain_core.tools import BaseTool

def tool(*args: Any, **kwargs: Any) -> Callable:
    """
    A decorator to define tools for DeepEye agents.
    It wraps langchain_core.tools.tool to provide a unified interface.
    
    Usage:
        @tool
        def my_tool(arg1: str) -> str:
            '''Tool description docstring.'''
            return "result"
            
        @tool(parse_docstring=True)
        def complex_tool(arg1: int):
            '''
            Args:
                arg1: Description of arg1
            '''
            ...
    """
    return lc_tool(*args, **kwargs)

class DeepEyeTool(BaseTool):
    """Base class for class-based tools if needed."""
    pass


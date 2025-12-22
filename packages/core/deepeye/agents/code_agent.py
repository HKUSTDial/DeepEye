from typing import Optional
from langchain_core.language_models import BaseChatModel
from deepeye.agents.base import ReActAgent
from deepeye.tools.sandbox import get_sandbox_tools
import os

CODE_AGENT_SYSTEM_PROMPT = """You are an Expert Data Analyst and Python Programmer.
Your goal is to analyze data, perform calculations, and generate visualizations using Python code.

Environment:
- You are running in a secure Docker Sandbox (Linux).
- Pre-installed libraries: pandas, numpy, matplotlib, seaborn, scipy, sklearn, yfinance, tabulate, openpyxl.
- Files provided to you are located in `/mnt/data/`.

Guidelines:
1. **SELF-CONTAINED CODE**: Every code block you write MUST be a complete, standalone script.
   - ALWAYS include all necessary imports (e.g., `import pandas as pd`, `import matplotlib.pyplot as plt`).
   - Do NOT assume variables from previous turns are preserved. Redefine them if needed.
2. **File Paths**: Use the absolute paths provided in the prompt (e.g., `/mnt/data/query_result.csv`).
3. **Visualizations**: Save plots to `/mnt/data/output.png` (or a descriptive name) unless asked otherwise. Do not use `plt.show()`.
4. **Error Handling**: If an error occurs, analyze it and rewrite the COMPLETE code to fix it.
5. **Output**: Print key results to stdout so I can see them.

Format your Python code cleanly.
"""

class CodeAgent(ReActAgent):
    """
    A specialized agent for general Data Analysis using Python in a Sandbox.
    """

    def __init__(
        self,
        model: BaseChatModel,
        sandbox_url: str | None = None,
        checkpointer: Optional[any] = None,
        system_prompt: str = CODE_AGENT_SYSTEM_PROMPT
    ):
        super().__init__(
            model=model,
            tools=get_sandbox_tools(sandbox_url),
            checkpointer=checkpointer,
            system_prompt=system_prompt
        )

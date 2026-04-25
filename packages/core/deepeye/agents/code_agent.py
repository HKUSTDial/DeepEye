from langchain_core.language_models import BaseChatModel
from langgraph.checkpoint.base import BaseCheckpointSaver

from deepeye.agents.react_agent import ReActAgent

CODE_AGENT_SYSTEM_PROMPT = """You are an Expert Data Analyst and Python Programmer.
Your goal is to analyze data, perform calculations, and generate visualizations using bash commands.

Environment:
- Linux sandbox with bash shell
- Pre-installed: Python 3.11, pandas, numpy, matplotlib, seaborn, scipy, sklearn, yfinance, tabulate, openpyxl
- Working directory: /workspace
- All files are in /workspace

**CRITICAL - Reuse First Principle**:
1. BEFORE creating any file or data, check if it already exists: `ls -la /workspace`
2. REUSE data from previous steps - you have memory of what you created earlier
3. If a file was created in a previous step, READ it instead of regenerating
4. Only create NEW files when explicitly requested or when nothing exists
5. Reference your previous work - you remember what commands you ran

Guidelines:
1. Use bash commands to accomplish tasks
2. Write Python code to files then execute: `echo 'code' > script.py && python script.py`
3. For multi-line scripts, use heredoc syntax:
   ```bash
   cat > script.py << 'EOF'
   import pandas as pd
   print('hello')
   EOF
   python script.py
   ```
4. Save plots to /workspace/output.png
5. Use pipes and Unix tools for data processing

Examples:
- Check existing files first: `ls -la /workspace`
- Read existing data: `cat /workspace/data.txt` or `head -10 /workspace/data.csv`
- Run Python: `python -c 'import pandas; print(pandas.__version__)'`
- List files: `ls -la /workspace`
"""


class CodeAgent(ReActAgent):
    """Data analysis agent with dedicated sandbox"""

    def __init__(
        self,
        model: BaseChatModel,
        tools: list,
        checkpointer: BaseCheckpointSaver | None = None,
        system_prompt: str = CODE_AGENT_SYSTEM_PROMPT,
        max_steps: int = 50,
    ):
        """
        Initialize CodeAgent with sandbox tools.
        
        Args:
            model: LLM model
            tools: Tool callables supplied by the application runtime
            checkpointer: LangGraph checkpointer
            system_prompt: System prompt
            max_steps: Maximum execution steps
            
        Example:
            sandbox = await runtime.create_sandbox(session_id)
            tools = runtime.create_sandbox_tools(sandbox)
            agent = CodeAgent(model=model, tools=tools)
        """
        super().__init__(
            model=model,
            tools=tools,
            system_prompt=system_prompt,
            checkpointer=checkpointer,
            max_steps=max_steps,
        )

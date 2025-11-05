"""DataCoder 节点的 Prompt 模板

该模块定义了 DataCoder 节点使用的所有 Prompt 模板常量。
采用结构化的 Markdown 格式，输出使用 XML 标签便于解析。
"""

# ============================================================================
# 初始代码生成提示词模板
# ============================================================================

INITIAL_CODE_GENERATION_PROMPT_SINGLE = """# Task Description
You are an expert Python data analyst. Generate Python code to process a pandas DataFrame based on user requirements.

# Code Execution Context
Your code will be executed in a sandboxed Docker environment with the following template:

```python
import pandas as pd
import numpy as np
import pickle
import base64

# === Input DataFrame is deserialized and available as 'df' ===
# df: pd.DataFrame
# Shape: (rows, columns)
# Columns: [column names will be provided]

# === YOUR CODE WILL BE INSERTED HERE ===
# TODO: Write your code here
# The input DataFrame is available as variable 'df' (also aliased as 'dataframe')
# You MUST assign the final result to variable 'result'
# === END OF YOUR CODE ===

# === Validation (automatically handled) ===
if 'result' not in locals():
    raise ValueError("Code must define 'result' variable")

if not isinstance(result, pd.DataFrame):
    raise TypeError(f"result must be DataFrame, but got {{type(result).__name__}}")
```

# Instructions
1. **Analyze the task**: Understand what operations are needed
2. **Write clean code**: Generate ONLY the code that needs to be filled in (between the markers)
3. **Use available variables**: Input DataFrame is `df` (or `dataframe`)
4. **Assign result**: Final result MUST be assigned to variable `result`
5. **Import additional libraries**: If you need libraries beyond pandas/numpy, import them in your code
6. **Best practices**: Use vectorized operations, handle edge cases, write efficient code

# Output Format
You MUST respond in the following structured format:

<think>
[Your analysis and reasoning]
- What operations are needed?
- What is the step-by-step approach?
- Any potential issues or edge cases?
- What libraries are needed?
</think>

<package_list>
[Comma-separated list of ALL required PyPI packages for your code]
Example: pandas, numpy, scikit-learn, scipy
</package_list>

<code>
[Your Python code to fill in the template]
</code>

# Input Data Information
{data_info}

# User Requirements
{task_description}

# Now Generate Code
Please generate the code for the given task following the exact output format above.
"""

INITIAL_CODE_GENERATION_PROMPT_MULTI = """# Task Description
You are an expert Python data analyst. Generate Python code to process MULTIPLE pandas DataFrames based on user requirements.

# Code Execution Context
Your code will be executed in a sandboxed Docker environment with the following template:

```python
import pandas as pd
import numpy as np
import pickle
import base64

# === Input DataFrames are deserialized and available as 'df0', 'df1', 'df2', ... ===
# df0: pd.DataFrame  # First DataFrame
# df1: pd.DataFrame  # Second DataFrame
# df2: pd.DataFrame  # Third DataFrame (if applicable)
# ...

# === YOUR CODE WILL BE INSERTED HERE ===
# TODO: Write your code here
# The input DataFrames are available as variables 'df0', 'df1', 'df2', etc.
# You MUST assign the final result to variable 'result'
# === END OF YOUR CODE ===

# === Validation (automatically handled) ===
if 'result' not in locals():
    raise ValueError("Code must define 'result' variable")

if not isinstance(result, pd.DataFrame):
    raise TypeError(f"result must be DataFrame, but got {{type(result).__name__}}")
```

# Instructions
1. **Analyze the task**: Understand what operations are needed across multiple DataFrames
2. **Write clean code**: Generate ONLY the code that needs to be filled in (between the markers)
3. **Use available variables**: Input DataFrames are `df0`, `df1`, `df2`, etc.
4. **Assign result**: Final result MUST be assigned to variable `result`
5. **Import additional libraries**: If you need libraries beyond pandas/numpy, import them in your code
6. **Best practices**: Use vectorized operations, handle edge cases, write efficient code
7. **Common operations**: merge, join, concat, comparison, etc.

# Output Format
You MUST respond in the following structured format:

<think>
[Your analysis and reasoning]
- What operations are needed?
- How should the DataFrames be combined/compared?
- What is the step-by-step approach?
- Any potential issues or edge cases?
- What libraries are needed?
</think>

<package_list>
[Comma-separated list of ALL required PyPI packages for your code]
Example: pandas, numpy, scikit-learn, scipy
</package_list>

<code>
[Your Python code to fill in the template]
</code>

# Input Data Information
{data_info}

# User Requirements
{task_description}

# Now Generate Code
Please generate the code for the given task following the exact output format above.
"""

# ============================================================================
# 代码修复提示词模板
# ============================================================================

CODE_FIX_PROMPT_SINGLE = """# Task Description
The previous code execution failed. Analyze the error and generate corrected code.

# Code Execution Context
Your code is executed in a sandboxed Docker environment with this template:

```python
import pandas as pd
import numpy as np
import pickle
import base64

# === Input DataFrame is deserialized and available as 'df' ===
# df: pd.DataFrame
# Shape: (rows, columns)
# Columns: [column names will be provided]

# === YOUR PREVIOUS CODE (FAILED) ===
[Your previous code will be shown below]
# === END OF YOUR CODE ===

# === Validation (automatically handled) ===
if 'result' not in locals():
    raise ValueError("Code must define 'result' variable")

if not isinstance(result, pd.DataFrame):
    raise TypeError(f"result must be DataFrame, but got {{type(result).__name__}}")
```

# Instructions
1. **Analyze the error**: Carefully read the error message and identify the root cause
2. **Understand the context**: Consider the DataFrame structure and data types
3. **Fix the issue**: Generate corrected code that resolves the error
4. **Verify logic**: Ensure the fixed code still fulfills the original requirements
5. **Handle edge cases**: Consider potential issues that might cause similar errors

# Output Format
You MUST respond in the following structured format:

<think>
[Your error analysis and solution approach]
- What is the error type and message?
- What is the root cause of this error?
- What specific issue needs to be fixed?
- What is the corrected approach?
- Are there any edge cases to handle?
</think>

<package_list>
[Comma-separated list of ALL required PyPI packages for the corrected code]
</package_list>

<code>
[The corrected Python code to fill in the template]
</code>

# Original Task Requirements
{task_description}

# Input Data Information
{data_info}

# Your Previous Code (FAILED)
```python
{failed_code}
```

# Error Information
```
{error_message}
```

# Now Fix the Error
Please analyze the error above and provide the corrected code following the exact output format.
"""

CODE_FIX_PROMPT_MULTI = """# Task Description
The previous code execution failed. Analyze the error and generate corrected code for MULTIPLE DataFrames.

# Code Execution Context
Your code is executed in a sandboxed Docker environment with this template:

```python
import pandas as pd
import numpy as np
import pickle
import base64

# === Input DataFrames are deserialized and available as 'df0', 'df1', 'df2', ... ===
# df0: pd.DataFrame  # First DataFrame
# df1: pd.DataFrame  # Second DataFrame
# df2: pd.DataFrame  # Third DataFrame (if applicable)
# ...

# === YOUR PREVIOUS CODE (FAILED) ===
[Your previous code will be shown below]
# === END OF YOUR CODE ===

# === Validation (automatically handled) ===
if 'result' not in locals():
    raise ValueError("Code must define 'result' variable")

if not isinstance(result, pd.DataFrame):
    raise TypeError(f"result must be DataFrame, but got {{type(result).__name__}}")
```

# Instructions
1. **Analyze the error**: Carefully read the error message and identify the root cause
2. **Understand the context**: Consider the DataFrame structures and data types
3. **Fix the issue**: Generate corrected code that resolves the error
4. **Verify logic**: Ensure the fixed code still fulfills the original requirements
5. **Handle edge cases**: Consider potential issues that might cause similar errors
6. **Multiple DataFrames**: Remember you have df0, df1, df2, etc. available

# Output Format
You MUST respond in the following structured format:

<think>
[Your error analysis and solution approach]
- What is the error type and message?
- What is the root cause of this error?
- What specific issue needs to be fixed?
- What is the corrected approach?
- Are there any edge cases to handle?
</think>

<package_list>
[Comma-separated list of ALL required PyPI packages for the corrected code]
</package_list>

<code>
[The corrected Python code to fill in the template]
</code>

# Original Task Requirements
{task_description}

# Input Data Information
{data_info}

# Your Previous Code (FAILED)
```python
{failed_code}
```

# Error Information
```
{error_message}
```

# Now Fix the Error
Please analyze the error above and provide the corrected code following the exact output format.
"""

# ============================================================================
# 辅助函数
# ============================================================================

def format_initial_prompt(
    task_description: str,
    data_info: str,
    is_multi_mode: bool = False
) -> str:
    """格式化初始代码生成提示词
    
    Args:
        task_description: 用户任务描述
        data_info: DataFrame 详细信息（已包含形状和列信息）
        is_multi_mode: 是否为多 DataFrame 模式
    
    Returns:
        格式化后的提示词
    """
    template = INITIAL_CODE_GENERATION_PROMPT_MULTI if is_multi_mode else INITIAL_CODE_GENERATION_PROMPT_SINGLE
    
    return template.format(
        task_description=task_description,
        data_info=data_info
    )


def format_fix_prompt(
    task_description: str,
    data_info: str,
    failed_code: str,
    error_message: str,
    is_multi_mode: bool = False
) -> str:
    """格式化代码修复提示词
    
    Args:
        task_description: 用户任务描述
        data_info: DataFrame 详细信息（已包含形状和列信息）
        failed_code: 失败的代码
        error_message: 错误信息
        is_multi_mode: 是否为多 DataFrame 模式
    
    Returns:
        格式化后的提示词
    """
    template = CODE_FIX_PROMPT_MULTI if is_multi_mode else CODE_FIX_PROMPT_SINGLE
    
    return template.format(
        task_description=task_description,
        data_info=data_info,
        failed_code=failed_code,
        error_message=error_message
    )


def extract_response_parts(response: str) -> tuple[str, list[str], str]:
    """从 LLM 响应中提取各个部分
    
    Args:
        response: LLM 的原始响应
    
    Returns:
        (think_content, package_list, code_content) 元组
        - think_content: 思考过程（如果没有则为空字符串）
        - package_list: 需要的包列表（如果没有则为空列表）
        - code_content: 代码内容
    """
    import re
    
    think_content = ""
    package_list = []
    code_content = ""
    
    # 提取 <think> 标签内容
    think_match = re.search(r'<think>(.*?)</think>', response, re.DOTALL | re.IGNORECASE)
    if think_match:
        think_content = think_match.group(1).strip()
    
    # 提取 <package_list> 标签内容
    package_match = re.search(r'<package_list>(.*?)</package_list>', response, re.DOTALL | re.IGNORECASE)
    if package_match:
        package_str = package_match.group(1).strip()
        if package_str:
            # 解析逗号分隔的包列表
            package_list = [pkg.strip() for pkg in package_str.split(',') if pkg.strip()]
    
    # 提取 <code> 标签内容
    code_match = re.search(r'<code>(.*?)</code>', response, re.DOTALL | re.IGNORECASE)
    if code_match:
        code_content = code_match.group(1).strip()
    else:
        # 如果没有找到 <code> 标签，尝试提取 markdown 代码块
        code_block_match = re.search(r'```(?:python)?\n(.*?)\n```', response, re.DOTALL)
        if code_block_match:
            code_content = code_block_match.group(1).strip()
        else:
            # 如果都没有，返回原始响应
            code_content = response.strip()
    
    # 清理代码（移除可能的 markdown 标记）
    code_content = _clean_code(code_content)
    
    return think_content, package_list, code_content


def _clean_code(code: str) -> str:
    """清理代码，移除 markdown 标记等
    
    Args:
        code: 原始代码
    
    Returns:
        清理后的代码
    """
    # 移除 markdown 代码块标记
    if code.startswith("```"):
        lines = code.split("\n")
        # 移除第一行（```python 或 ```）
        lines = lines[1:]
        # 移除最后一行（```）
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        code = "\n".join(lines)
    
    return code.strip()


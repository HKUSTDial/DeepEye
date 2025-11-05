"""DataPlot 节点的 Prompt 模板

该模块定义了 DataPlot 节点使用的所有 Prompt 模板常量。
采用 Code Filling 任务设计，明确告诉 LLM 生成中间部分代码。
"""

# ============================================================================
# 初始代码生成提示词模板
# ============================================================================

INITIAL_CODE_GENERATION_PROMPT_SINGLE = """# Task Description
You are an expert Python data visualization specialist. Generate Python code to create visualizations from a pandas DataFrame based on user requirements.

# Code Execution Context
Your code will be executed in a sandboxed Docker environment with the following template:

```python
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import seaborn as sns

# === Input DataFrame is deserialized and available as 'df' ===
# df: pd.DataFrame
# Shape: (rows, columns)
# Columns: [column names will be provided]

# === Plot directory is prepared ===
PLOT_DIR = "/sandbox/plots"  # All plots must be saved here

# === YOUR CODE WILL BE INSERTED HERE ===
# TODO: Write your visualization code here
# The input DataFrame is available as variable 'df' (also aliased as 'dataframe')
# You MUST save all plots to PLOT_DIR using descriptive filenames
# After saving each plot, print the metadata in this exact format:
# PLOT_FILE: <filename>|<detailed_description>|<format>
# Where <detailed_description> should be 2-4 sentences explaining:
#   - Chart type and what it shows
#   - What axes represent (with units)
#   - Main patterns/trends observed
#   - Key insights or notable observations
# === END OF YOUR CODE ===

# === Output validation (automatically handled) ===
# The system will automatically collect all saved plot files
```

# Instructions
1. **Analyze the task**: Understand what visualizations are needed
2. **Write clean code**: Generate ONLY the code that needs to be filled in (between the markers)
3. **Use available variables**: Input DataFrame is `df` (or `dataframe`)
4. **Save plots**: Save ALL plots to `PLOT_DIR` with descriptive filenames (e.g., "sales_trend.png")
5. **Print metadata with DETAILED descriptions**: After saving each plot, print metadata in this exact format:
   ```python
   print('PLOT_FILE: sales_trend.png|A line chart showing monthly sales trends from January to December 2024. The x-axis represents months and y-axis shows sales amount in USD. The chart reveals a steady upward trend with a peak in November, indicating strong Q4 performance. Key insight: 35% growth compared to Q1.|png')
   ```
   
   **Description Requirements** (the middle part between first and last `|`):
   - Start with the chart type (e.g., "A bar chart showing...", "A scatter plot displaying...")
   - Explain what the axes represent (x-axis, y-axis, and their units if applicable)
   - Describe the main pattern, trend, or relationship shown
   - Include key insights or notable observations (e.g., peaks, outliers, correlations)
   - Mention any important data characteristics (ranges, distributions, groupings)
   - Length: 2-4 sentences, be informative and specific
   
6. **Import additional libraries**: If you need libraries beyond matplotlib/seaborn, import them in your code
7. **Best practices**: 
   - Use clear titles, labels, and legends
   - Choose appropriate chart types
   - **IMPORTANT: Use ENGLISH ONLY for all text in plots (titles, labels, legends, annotations). DO NOT use Chinese or other non-ASCII characters.**
   - Close figures after saving to free memory: `plt.close()`

# Output Format
You MUST respond in the following structured format:

<think>
[Your analysis and reasoning]
- What type of visualization is most suitable?
- What data columns will be used?
- What is the step-by-step approach?
- Any special considerations (e.g., data preprocessing, styling)?
- What libraries are needed?
</think>

<package_list>
[Comma-separated list of ALL required PyPI packages for your code]
Example: matplotlib, seaborn, plotly
</package_list>

<code>
[Your Python code to fill in the template]
</code>

# Input Data Information
{data_info}

# User Requirements
{task_description}

# Now Generate Code
Please generate the visualization code for the given task following the exact output format above.
"""

INITIAL_CODE_GENERATION_PROMPT_MULTI = """# Task Description
You are an expert Python data visualization specialist. Generate Python code to create visualizations from MULTIPLE pandas DataFrames based on user requirements.

# Code Execution Context
Your code will be executed in a sandboxed Docker environment with the following template:

```python
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import seaborn as sns

# === Input DataFrames are deserialized and available as 'df0', 'df1', 'df2', ... ===
# df0: pd.DataFrame  # First DataFrame
# df1: pd.DataFrame  # Second DataFrame
# df2: pd.DataFrame  # Third DataFrame (if applicable)
# ...

# === Plot directory is prepared ===
PLOT_DIR = "/sandbox/plots"  # All plots must be saved here

# === YOUR CODE WILL BE INSERTED HERE ===
# TODO: Write your visualization code here
# The input DataFrames are available as variables 'df0', 'df1', 'df2', etc.
# You MUST save all plots to PLOT_DIR using descriptive filenames
# After saving each plot, print the metadata in this exact format:
# PLOT_FILE: <filename>|<detailed_description>|<format>
# Where <detailed_description> should be 2-4 sentences explaining:
#   - Chart type and what it shows
#   - What axes represent (with units)
#   - Main patterns/trends observed
#   - Key insights or notable observations
#   - How multiple DataFrames relate (if applicable)
# === END OF YOUR CODE ===

# === Output validation (automatically handled) ===
# The system will automatically collect all saved plot files
```

# Instructions
1. **Analyze the task**: Understand what visualizations are needed across multiple DataFrames
2. **Write clean code**: Generate ONLY the code that needs to be filled in (between the markers)
3. **Use available variables**: Input DataFrames are `df0`, `df1`, `df2`, etc.
4. **Save plots**: Save ALL plots to `PLOT_DIR` with descriptive filenames (e.g., "comparison_chart.png")
5. **Print metadata with DETAILED descriptions**: After saving each plot, print metadata in this exact format:
   ```python
   print('PLOT_FILE: regional_comparison.png|A grouped bar chart comparing quarterly sales performance across three regions (North, South, East). The x-axis shows quarters (Q1-Q4 2024) and y-axis represents sales revenue in thousands of USD. North region consistently outperforms others with 45% higher average sales. Notable spike in Q4 across all regions indicates successful holiday campaigns.|png')
   ```
   
   **Description Requirements** (the middle part between first and last `|`):
   - Start with the chart type (e.g., "A bar chart showing...", "A scatter plot displaying...")
   - Explain what the axes represent (x-axis, y-axis, and their units if applicable)
   - Describe the main pattern, trend, or relationship shown
   - Include key insights or notable observations (e.g., peaks, outliers, correlations)
   - Mention any important data characteristics (ranges, distributions, groupings)
   - For multi-DataFrame plots, clearly explain what each dataset represents and how they relate
   - Length: 2-4 sentences, be informative and specific
   
6. **Import additional libraries**: If you need libraries beyond matplotlib/seaborn, import them in your code
7. **Best practices**: 
   - Use clear titles, labels, and legends
   - Choose appropriate chart types for comparisons
   - **IMPORTANT: Use ENGLISH ONLY for all text in plots (titles, labels, legends, annotations). DO NOT use Chinese or other non-ASCII characters.**
   - Close figures after saving to free memory: `plt.close()`
8. **Common operations**: Compare data, create subplots, overlay multiple datasets, etc.

# Output Format
You MUST respond in the following structured format:

<think>
[Your analysis and reasoning]
- What type of visualization is most suitable?
- How should the DataFrames be compared/combined?
- What data columns will be used from each DataFrame?
- What is the step-by-step approach?
- Any special considerations (e.g., data preprocessing, styling)?
- What libraries are needed?
</think>

<package_list>
[Comma-separated list of ALL required PyPI packages for your code]
Example: matplotlib, seaborn, plotly
</package_list>

<code>
[Your Python code to fill in the template]
</code>

# Input Data Information
{data_info}

# User Requirements
{task_description}

# Now Generate Code
Please generate the visualization code for the given task following the exact output format above.
"""

# ============================================================================
# 代码修复提示词模板
# ============================================================================

CODE_FIX_PROMPT_SINGLE = """# Task Description
The previous visualization code execution failed. Analyze the error and generate corrected code.

# Code Execution Context
Your code is executed in a sandboxed Docker environment with this template:

```python
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import seaborn as sns

# === Input DataFrame is deserialized and available as 'df' ===
# df: pd.DataFrame
# Shape: (rows, columns)
# Columns: [column names will be provided]

# === Plot directory is prepared ===
PLOT_DIR = "/sandbox/plots"  # All plots must be saved here

# === YOUR PREVIOUS CODE (FAILED) ===
[Your previous code will be shown below]
# === END OF YOUR CODE ===

# === Output validation (automatically handled) ===
# The system will automatically collect all saved plot files
```

# Instructions
1. **Analyze the error**: Carefully read the error message and identify the root cause
2. **Understand the context**: Consider the DataFrame structure and data types
3. **Fix the issue**: Generate corrected code that resolves the error
4. **Verify logic**: Ensure the fixed code still fulfills the original visualization requirements
5. **Handle edge cases**: Consider potential issues that might cause similar errors
6. **Print metadata with DETAILED descriptions**: After saving each plot, print metadata with detailed 2-4 sentence descriptions following the format:
   ```python
   print('PLOT_FILE: filename.png|A [chart type] showing [what]. The x-axis represents [description with units] and y-axis shows [description with units]. [Main pattern/trend]. [Key insight or observation].|png')
   ```
7. **IMPORTANT: Use ENGLISH ONLY for all text in plots (titles, labels, legends, annotations). DO NOT use Chinese or other non-ASCII characters.**

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
The previous visualization code execution failed. Analyze the error and generate corrected code for MULTIPLE DataFrames.

# Code Execution Context
Your code is executed in a sandboxed Docker environment with this template:

```python
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import seaborn as sns

# === Input DataFrames are deserialized and available as 'df0', 'df1', 'df2', ... ===
# df0: pd.DataFrame  # First DataFrame
# df1: pd.DataFrame  # Second DataFrame
# df2: pd.DataFrame  # Third DataFrame (if applicable)
# ...

# === Plot directory is prepared ===
PLOT_DIR = "/sandbox/plots"  # All plots must be saved here

# === YOUR PREVIOUS CODE (FAILED) ===
[Your previous code will be shown below]
# === END OF YOUR CODE ===

# === Output validation (automatically handled) ===
# The system will automatically collect all saved plot files
```

# Instructions
1. **Analyze the error**: Carefully read the error message and identify the root cause
2. **Understand the context**: Consider the DataFrame structures and data types
3. **Fix the issue**: Generate corrected code that resolves the error
4. **Verify logic**: Ensure the fixed code still fulfills the original visualization requirements
5. **Handle edge cases**: Consider potential issues that might cause similar errors
6. **Multiple DataFrames**: Remember you have df0, df1, df2, etc. available
7. **Print metadata with DETAILED descriptions**: After saving each plot, print metadata with detailed 2-4 sentence descriptions following the format:
   ```python
   print('PLOT_FILE: filename.png|A [chart type] showing [what]. The x-axis represents [description with units] and y-axis shows [description with units]. [Main pattern/trend]. [Key insight or observation]. [How multiple DataFrames relate if applicable].|png')
   ```
8. **IMPORTANT: Use ENGLISH ONLY for all text in plots (titles, labels, legends, annotations). DO NOT use Chinese or other non-ASCII characters.**

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

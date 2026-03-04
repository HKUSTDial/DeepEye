"""Compatibility shim for report_module pipeline: execute_python_code and clean_html.

Used when running the report pipeline from the backend without modifying report_module.
"""

from __future__ import annotations

import io
import sys
from typing import Any
import re
import io
import contextlib
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import pandas as pd

try:
    import plotly.express as px
except ImportError:
    px = None



def execute_python_code(code: str, data_context):
    """
    执行 LLM 生成的 Python 代码并捕获输出。

    兼容多表模式 (dfs) 和 单表模式 (df)。

    Args:
        code: Python 代码字符串
        data_context: 可以是单个 pd.DataFrame，也可以是包含多个 DataFrame 的字典 {'table_name': df}
    """
    # 1. 基础执行环境
    local_vars = {"pd": pd, "px": px, "np": np, "go": go}

    # 2. 关键修改：智能注入变量名
    # 如果传入的是字典，说明是多表模式，注入变量名 'dfs'
    if isinstance(data_context, dict):
        local_vars["dfs"] = data_context
    # 否则默认为单表模式，注入变量名 'df' (兼容旧代码)
    else:
        local_vars["df"] = data_context

    output_buffer = io.StringIO()

    try:
        # 3. 捕获 print() 的输出并执行
        with contextlib.redirect_stdout(output_buffer):
            exec(code,local_vars,local_vars)

        # 获取文本输出
        text_output = output_buffer.getvalue()

        # 获取可能生成的图表对象
        fig = local_vars.get('fig', None)

        return {"success": True, "text": text_output, "fig": fig}
    except Exception as e:
        return {"success": False, "error": str(e), "text": "", "fig": None}
def clean_html(html: str) -> str:
    """Optional HTML sanitization; pipeline imports it but may not use."""
    if not html or not isinstance(html, str):
        return ""
    return html.strip()

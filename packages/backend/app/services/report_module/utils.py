# utils.py
import re
import io
import contextlib
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go


def clean_html(text: str) -> str:
    """清理 LLM 输出中的 markdown 标记"""
    text = re.sub(r'^```(html)?\s*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\s*```$', '', text)
    return text.strip()


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
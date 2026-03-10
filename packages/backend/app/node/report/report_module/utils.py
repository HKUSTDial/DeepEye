# utils.py
import re
import io
import contextlib
from html import escape

import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

_PLOTLY_SCRIPT_RE = re.compile(r"<script[^>]+src=[\"'][^\"']*plotly[^\"']*[\"'][^>]*></script>", re.IGNORECASE)
_PLOTLY_CONFIG_RE = re.compile(r"<script>\s*window\.PlotlyConfig\s*=\s*\{[^<]*</script>", re.IGNORECASE)

_REPORT_CHART_MIN_HEIGHT = 360
_REPORT_CHART_MAX_HEIGHT = 560
_REPORT_CHART_DEFAULT_HEIGHT = 460


def clean_html(text: str) -> str:
    """清理 LLM 输出中的 markdown 标记"""
    text = re.sub(r'^```(html)?\s*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\s*```$', '', text)
    return text.strip()


def normalize_report_chart_height(raw_height: object, trace_count: int = 0) -> int:
    """Return a bounded chart height suitable for narrow report layouts."""
    if isinstance(raw_height, (int, float)) and not isinstance(raw_height, bool):
        return max(_REPORT_CHART_MIN_HEIGHT, min(int(raw_height), _REPORT_CHART_MAX_HEIGHT))
    if trace_count >= 5:
        return 520
    if trace_count >= 3:
        return 500
    return _REPORT_CHART_DEFAULT_HEIGHT


def build_report_chart_placeholder_html(message: str) -> str:
    safe_message = escape(message.strip() or "Chart unavailable for this section.")
    return (
        '<div class="report-chart-empty">'
        '<div class="report-chart-empty-icon">📊</div>'
        '<div class="report-chart-empty-title">Chart unavailable</div>'
        f'<div class="report-chart-empty-body">{safe_message}</div>'
        '</div>'
    )


def sanitize_report_chart_html(chart_html: str) -> str:
    sanitized = chart_html.strip()
    sanitized = _PLOTLY_SCRIPT_RE.sub("", sanitized)
    sanitized = _PLOTLY_CONFIG_RE.sub("", sanitized)
    return f'<div class="report-chart-embed">{sanitized}</div>' if sanitized else ""


def render_plotly_figure_for_report(fig: go.Figure) -> str:
    """Serialize a Plotly figure into report-safe responsive HTML."""
    figure_dict = fig.to_dict()
    layout = figure_dict.setdefault("layout", {})
    if not isinstance(layout, dict):
        layout = {}
        figure_dict["layout"] = layout

    layout.pop("width", None)
    layout["autosize"] = True
    chart_height = normalize_report_chart_height(layout.get("height"), len(figure_dict.get("data", [])))
    layout["height"] = chart_height

    margin = layout.get("margin")
    if not isinstance(margin, dict):
        margin = {}
    margin.setdefault("l", 48)
    margin.setdefault("r", 24)
    margin.setdefault("t", 56)
    margin.setdefault("b", 48)
    layout["margin"] = margin

    normalized_fig = go.Figure(figure_dict)
    chart_html = normalized_fig.to_html(
        full_html=False,
        include_plotlyjs=False,
        config={"responsive": True, "displayModeBar": False},
        default_width="100%",
        default_height=f"{chart_height}px",
    )
    return sanitize_report_chart_html(chart_html)


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

from .base import BaseTool
from pydantic import Field, ConfigDict
from typing import List, Dict, Any, Optional, Literal
import json

_CHART_GENERATION_DESCRIPTION = """A tool to generate ECharts option (and optional HTML) from structured data.
Supported chart types: line, bar, pie, scatter. Accepts data series and xAxis categories.
Return ECharts option JSON by default; can also return a full HTML snippet for preview.
"""


class ChartGeneration(BaseTool):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    name: str = "chart_generation"
    description: str = _CHART_GENERATION_DESCRIPTION
    parameters: dict = {
        "type": "object",
        "properties": {
            "chart_type": {
                "type": "string",
                "enum": ["line", "bar", "pie", "scatter"],
                "description": "The chart type to generate."
            },
            "title": {
                "type": "string",
                "description": "Main title displayed on the chart."
            },
            "subtitle": {
                "type": "string",
                "description": "Subtitle displayed under the main title."
            },
            "x_axis": {
                "type": "array",
                "items": {"type": "string"},
                "description": "xAxis categories for line/bar charts. Not used for pie."
            },
            "series": {
                "type": "array",
                "description": "Series list. For line/bar/scatter: [{name, data}]. For pie: [{name, value}] in one series.",
                "items": {
                    "type": "object"
                }
            },
            "legend": {
                "type": "boolean",
                "description": "Whether to show legend.",
                "default": True
            },
            "show_toolbox": {
                "type": "boolean",
                "description": "Whether to show toolbox (saveAsImage, dataView).",
                "default": True
            },
            "as_html": {
                "type": "boolean",
                "description": "If true, return a complete HTML page string embedding ECharts option.",
                "default": False
            },
            "width": {
                "type": "string",
                "description": "Chart container CSS width (when as_html is true).",
                "default": "100%"
            },
            "height": {
                "type": "string",
                "description": "Chart container CSS height (when as_html is true).",
                "default": "480px"
            }
        },
        "required": ["chart_type", "series"],
        "additionalProperties": False
    }

    async def execute(
        self,
        chart_type: Literal["line", "bar", "pie", "scatter"],
        series: List[Dict[str, Any]],
        title: Optional[str] = None,
        subtitle: Optional[str] = None,
        x_axis: Optional[List[str]] = None,
        legend: bool = True,
        show_toolbox: bool = True,
        as_html: bool = False,
        width: str = "100%",
        height: str = "480px",
    ) -> str:
        option = self._build_option(
            chart_type=chart_type,
            series=series,
            title=title,
            subtitle=subtitle,
            x_axis=x_axis,
            legend=legend,
            show_toolbox=show_toolbox,
        )
        if as_html:
            return self._wrap_html(option, width=width, height=height)
        return json.dumps(option, ensure_ascii=False, indent=2)

    def _build_option(
        self,
        chart_type: str,
        series: List[Dict[str, Any]],
        title: Optional[str],
        subtitle: Optional[str],
        x_axis: Optional[List[str]],
        legend: bool,
        show_toolbox: bool,
    ) -> Dict[str, Any]:
        option: Dict[str, Any] = {
            "tooltip": {"trigger": "item" if chart_type == "pie" else "axis"},
        }
        if title or subtitle:
            option["title"] = {"text": title or "", "subtext": subtitle or ""}
        if legend:
            option["legend"] = {"type": "scroll"}
        if show_toolbox:
            option["toolbox"] = {
                "feature": {
                    "saveAsImage": {},
                    "dataView": {"readOnly": False},
                    "restore": {},
                    "magicType": {"type": ["line", "bar"]},
                }
            }

        if chart_type in ("line", "bar", "scatter"):
            option["xAxis"] = {"type": "category", "data": x_axis or []}
            option["yAxis"] = {"type": "value"}
            built_series: List[Dict[str, Any]] = []
            for s in series:
                built_series.append({
                    "name": s.get("name", "series"),
                    "type": chart_type,
                    "data": s.get("data", []),
                    "smooth": True if chart_type == "line" else False,
                })
            option["series"] = built_series
        elif chart_type == "pie":
            # For pie, expect series like: [{"name": "A", "value": 10}, ...]
            option["legend"] = option.get("legend", {})
            option["series"] = [
                {
                    "name": title or "",
                    "type": "pie",
                    "radius": "50%",
                    "data": [{"name": d.get("name"), "value": d.get("value")} for d in series],
                    "emphasis": {"itemStyle": {"shadowBlur": 10, "shadowOffsetX": 0, "shadowColor": "rgba(0, 0, 0, 0.5)"}},
                }
            ]
        else:
            raise ValueError(f"Unsupported chart_type: {chart_type}")

        return option

    def _wrap_html(self, option: Dict[str, Any], width: str, height: str) -> str:
        option_json = json.dumps(option, ensure_ascii=False)
        html = f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>ECharts Preview</title>
  <script src=\"https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js\"></script>
  <style>
    #main {{ width: {width}; height: {height}; }}
    html, body {{ margin: 0; padding: 0; }}
  </style>
</head>
<body>
  <div id=\"main\"></div>
  <script>
    const option = {option_json};
    const dom = document.getElementById('main');
    const chart = echarts.init(dom);
    chart.setOption(option);
    window.addEventListener('resize', () => chart.resize());
  </script>
  </body>
</html>
"""
        return html


if __name__ == "__main__":
    import asyncio
    async def _demo():
        tool = ChartGeneration()
        option_json = await tool.execute(
            chart_type="line",
            title="Sales over Months",
            x_axis=["Jan", "Feb", "Mar"],
            series=[
                {"name": "Product A", "data": [120, 132, 101]},
                {"name": "Product B", "data": [220, 182, 191]},
            ],
        )
        print(option_json)
    asyncio.run(_demo())
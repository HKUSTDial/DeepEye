import argparse
import asyncio
from pathlib import Path
from typing import List, Dict, Any

from app.tool.text2sql import Text2SQL
from app.tool.sqlite_database import SQLiteDatabase
from app.tool.chart_generation import ChartGeneration
from app.config.config import config


def infer_chart_from_result(column_names: List[str], rows: List[list]) -> Dict[str, Any]:
    """Heuristic mapping from SQL result to a basic ECharts option inputs.
    - If 2 columns and second is numeric → bar chart with first as xAxis
    - If 3+ columns or non-numeric → fallback to line using first col as xAxis and others as series
    """
    def is_numeric_column(values: List[Any]) -> bool:
        try:
            for v in values:
                if v is None:
                    continue
                float(v)
            return True
        except Exception:
            return False

    if not rows:
        return {
            "chart_type": "bar",
            "title": "Empty Result",
            "x_axis": [],
            "series": [],
        }

    # transpose rows to columns for detection
    cols = list(zip(*rows)) if rows and rows[0] else []
    if len(column_names) == 2 and len(cols) == 2 and is_numeric_column(list(cols[1])):
        x_axis = [str(x) for x in cols[0]]
        series = [{"name": column_names[1], "data": [float(v) if v is not None else None for v in cols[1]]}]
        return {
            "chart_type": "bar",
            "title": f"{column_names[0]} vs {column_names[1]}",
            "x_axis": x_axis,
            "series": series,
        }

    # otherwise: treat first column as category, rest numeric series
    x_axis = [str(x) for x in cols[0]]
    series = []
    for idx in range(1, len(column_names)):
        col_vals = list(cols[idx]) if idx < len(cols) else []
        if is_numeric_column(col_vals):
            series.append({
                "name": column_names[idx],
                "data": [float(v) if v is not None else None for v in col_vals]
            })
    if not series:
        # all non-numeric → count frequency as pie
        from collections import Counter
        cnt = Counter(x_axis)
        pie_data = [{"name": k, "value": v} for k, v in cnt.items()]
        return {
            "chart_type": "pie",
            "title": column_names[0],
            "series": pie_data,
        }
    return {
        "chart_type": "line",
        "title": ", ".join(column_names[1:]),
        "x_axis": x_axis,
        "series": series,
    }


async def run(question: str, out: Path, as_html: bool, width: str, height: str) -> Path:
    t2s = Text2SQL()
    sql = await t2s.execute(question)
    db = SQLiteDatabase()
    result = await db.execute(sql)

    mapping = infer_chart_from_result(result["column_names"], result["rows"])

    chart = ChartGeneration()
    html_or_json = await chart.execute(
        chart_type=mapping.get("chart_type", "bar"),
        title=mapping.get("title"),
        x_axis=mapping.get("x_axis"),
        series=mapping.get("series", []),
        as_html=as_html,
        width=width,
        height=height,
    )

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html_or_json, encoding="utf-8")
    return out


def main():
    parser = argparse.ArgumentParser(description="Text2SQL -> Execute -> Visualize (ECharts)")
    parser.add_argument("question", type=str, help="Natural language question to convert and query")
    parser.add_argument("--out", type=str, default="/home/xieyupeng/DeepEye/files/charts/auto_viz.html", help="Output path (.html for HTML, .json for option)")
    parser.add_argument("--as-html", action="store_true", help="Output full HTML instead of JSON option")
    parser.add_argument("--width", type=str, default="100%", help="Chart width for HTML output")
    parser.add_argument("--height", type=str, default="480px", help="Chart height for HTML output")
    parser.add_argument("--db", type=str, default=None, help="Override SQLite database path (optional)")
    args = parser.parse_args()

    # Optional runtime override for DB path
    if args.db:
        config.sqlite_database_config.path = args.db

    out_path = Path(args.out)
    asyncio.run(run(args.question, out_path, args.as_html, args.width, args.height))
    print(str(out_path))


if __name__ == "__main__":
    main()



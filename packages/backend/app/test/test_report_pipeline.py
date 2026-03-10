from __future__ import annotations

import pandas as pd
import plotly.express as px

from app.node.report.report_module.pipeline import AutoReportPipeline
from app.node.report.report_module.utils import (
    build_report_chart_placeholder_html,
    render_plotly_figure_for_report,
)


def test_render_plotly_figure_for_report_normalizes_dimensions_and_scripts() -> None:
    df = pd.DataFrame(
        {
            "city": ["Zurich", "Amsterdam", "Geneva"],
            "revenue": [120, 95, 88],
        }
    )
    fig = px.bar(df, x="city", y="revenue", title="Weekly Revenue")
    fig.update_layout(width=1400, height=820)

    html = render_plotly_figure_for_report(fig)

    assert "report-chart-embed" in html
    assert "plotly-latest.min.js" not in html
    assert "plotly-3.4.0.min.js" not in html
    assert '"width":1400' not in html
    assert '"height":820' not in html
    assert '"height":560' in html
    assert '"responsive": true' in html.lower()


def test_build_report_chart_placeholder_html_contains_message() -> None:
    html = build_report_chart_placeholder_html("No chart was generated for this section.")

    assert "report-chart-empty" in html
    assert "Chart unavailable" in html
    assert "No chart was generated for this section." in html


def test_render_html_includes_chart_shell_and_placeholder(tmp_path) -> None:
    pipeline = AutoReportPipeline.__new__(AutoReportPipeline)
    pipeline.progress_callback = None
    output_path = tmp_path / "report.html"

    pipeline.render_html(
        kpis=[
            {
                "label": "Top City",
                "value": "Zurich",
                "trend_color": "blue",
                "trend": "Stable",
                "sub_label": "Highest revenue",
            }
        ],
        analysis_results=[
            {
                "title": "Revenue Trend",
                "desc": "Revenue trend insight.",
                "chart_html": build_report_chart_placeholder_html("Chart generation code failed."),
            }
        ],
        summary="Summary content.",
        conclusion="<p>Conclusion content.</p>",
        title="Data Analysis Report",
        output_file=str(output_path),
        template_name="template_1.html",
    )

    content = output_path.read_text(encoding="utf-8")

    assert "report-chart-shell" in content
    assert "report-chart-empty" in content
    assert "Chart generation code failed." in content

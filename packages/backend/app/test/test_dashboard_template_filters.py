"""Tests for dashboard template filter coercion logic."""

from __future__ import annotations

import importlib
import os

import pandas as pd

os.environ.setdefault("ALLOW_INSECURE_DEFAULTS", "true")
os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_BASE_URL", "http://localhost:8000")
os.environ.setdefault("LLM_MODEL", "test-model")


template_app = importlib.import_module("app.node.dashboard.nl2dashboard.engineering.template.app")


def test_apply_filters_coerces_string_numbers_for_select_filters() -> None:
    df = pd.DataFrame(
        {
            "store_id": [101, 102, 103],
            "city": ["Shanghai", "Beijing", "Shenzhen"],
        }
    )

    filtered = template_app.apply_filters(
        df,
        {"store_id": {"operator": "equals", "value": "102"}},
    )

    assert filtered["city"].tolist() == ["Beijing"]


def test_apply_filters_coerces_string_dates_for_between_filters() -> None:
    df = pd.DataFrame(
        {
            "week_start": pd.to_datetime(["2025-10-06", "2025-10-13", "2025-10-20"]),
            "revenue": [100, 200, 300],
        }
    )

    filtered = template_app.apply_filters(
        df,
        {"week_start": {"operator": "between", "value": ["2025-10-10", "2025-10-18"]}},
    )

    assert filtered["revenue"].tolist() == [200]

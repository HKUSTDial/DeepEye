from __future__ import annotations

from typing import Any

import pandas as pd


def accumulate_token_usage(usage: dict[str, Any], token_usage: dict[str, Any] | None) -> None:
    """Accumulate token usage counters into a shared total dictionary."""
    if token_usage is not None:
        token_usage["prompt_tokens"] += usage.get("prompt_tokens", 0)
        token_usage["completion_tokens"] += usage.get("completion_tokens", 0)
        token_usage["total_tokens"] += usage.get("total_tokens", 0)


def compare_numeric_value(value: Any, threshold: float, operator: str) -> bool:
    """Compare a value with a numeric threshold, accepting numeric strings."""
    if value is None:
        return False

    try:
        if isinstance(value, str):
            numeric_value = float(value)
        elif isinstance(value, (int, float)):
            numeric_value = float(value)
        else:
            return False
    except (ValueError, TypeError):
        return False

    if operator == ">":
        return numeric_value > threshold
    if operator == "<":
        return numeric_value < threshold
    if operator == ">=":
        return numeric_value >= threshold
    if operator == "<=":
        return numeric_value <= threshold
    return False


def list_to_dataframe(data: list[dict]) -> pd.DataFrame:
    """Convert a list of dictionaries to a pandas DataFrame."""
    if not data:
        return pd.DataFrame()
    return pd.DataFrame(data)


def dataframe_to_list(df: pd.DataFrame) -> list[dict]:
    """Convert a pandas DataFrame to records with pandas missing values normalized."""
    if df.empty:
        return []
    return df.replace({pd.NA: None, pd.NaT: None}).to_dict("records")


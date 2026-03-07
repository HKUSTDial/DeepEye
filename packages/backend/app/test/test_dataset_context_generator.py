from __future__ import annotations

import pandas as pd

from app.node.report.report_module.DatasetContextGenerator import DatasetContextGenerator


def test_generate_context_treats_boolean_columns_as_categorical(monkeypatch) -> None:
    for key in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY", "all_proxy"):
        monkeypatch.delenv(key, raising=False)
    generator = DatasetContextGenerator(
        api_key="test-key",
        model_name="test-model",
        max_tokens=512,
    )
    monkeypatch.setattr(
        generator,
        "_generate_column_names_and_summary",
        lambda *args, **kwargs: {
            "full_column_names": {
                "city": "city",
                "is_priority_market": "is_priority_market",
                "revenue": "revenue",
            },
            "dataset_summary": "test summary",
        },
    )

    df = pd.DataFrame(
        {
            "city": ["Hangzhou", "Shenzhen", "Shanghai", "Beijing"],
            "is_priority_market": [True, False, True, False],
            "revenue": [120.0, 95.0, 102.0, 88.0],
        }
    )

    context = generator.generate_context(df, dataset_name="test_dataset")

    assert "is_priority_market" in context["categorical_details"]
    assert "is_priority_market" not in context["numerical_details"]
    assert context["fields_info"]["is_priority_market"]["semantic_type"] == "CATEGORY"
    assert "revenue" in context["numerical_details"]

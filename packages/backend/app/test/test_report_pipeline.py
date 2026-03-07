from app.node.report.report_module.DatasetContextGenerator import _normalize_report_max_tokens as normalize_context_max_tokens
from app.node.report.report_module.pipeline import _normalize_report_max_tokens as normalize_pipeline_max_tokens


def test_report_pipeline_clamps_max_tokens() -> None:
    assert normalize_pipeline_max_tokens(20000) == 8192
    assert normalize_pipeline_max_tokens(1024) == 1024
    assert normalize_pipeline_max_tokens(0) is None


def test_dataset_context_generator_clamps_max_tokens() -> None:
    assert normalize_context_max_tokens(20000) == 8192
    assert normalize_context_max_tokens(2048) == 2048
    assert normalize_context_max_tokens(-1) is None

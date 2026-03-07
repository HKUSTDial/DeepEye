import json
import os

os.environ.setdefault("ALLOW_INSECURE_DEFAULTS", "true")
os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_BASE_URL", "http://localhost:8000")
os.environ.setdefault("LLM_MODEL", "test-model")

from app.node.dashboard.nl2dashboard.engineering.dashboard_engineer import DashboardEngineer


def test_dashboard_engineer_creates_public_data_dir_before_copy(tmp_path, monkeypatch) -> None:
    dataset_path = tmp_path / "input.csv"
    dataset_path.write_text("city,total_revenue\nHangzhou,100.0\n", encoding="utf-8")

    output_path = tmp_path / "output"
    output_path.mkdir()
    (output_path / "dashboard_config.json").write_text(json.dumps({"layout": {}, "blocks": []}), encoding="utf-8")

    engineer = DashboardEngineer(llm_client=None, model="test-model")
    monkeypatch.setattr(engineer, "_process_dashboard_config", lambda *args, **kwargs: None)
    monkeypatch.setattr(engineer, "_select_template_by_config", lambda *args, **kwargs: "default")
    monkeypatch.setattr(engineer, "_apply_template_with_substitution", lambda *args, **kwargs: True)
    monkeypatch.setattr(engineer, "_update_page_template_config", lambda *args, **kwargs: None)
    monkeypatch.setattr(engineer, "_update_app_config", lambda *args, **kwargs: None)
    monkeypatch.setattr(engineer, "_update_config_with_html_names", lambda *args, **kwargs: None)

    va_app_path = engineer._build_va_system(
        output_path=str(output_path),
        dataset_path=str(dataset_path),
        question="Show city revenue ranking",
        design_result={},
    )

    copied_dataset = os.path.join(va_app_path, "public", "data", dataset_path.name)
    assert os.path.exists(copied_dataset)

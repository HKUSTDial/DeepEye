import json
import os
from types import SimpleNamespace

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
    (output_path / "dashboard_config.json").write_text(
        json.dumps({"layout": {}, "blocks": [], "dataSource": {"path": "/data/"}}),
        encoding="utf-8",
    )

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

    copied_config = os.path.join(va_app_path, "public", "configs", "dashboard_config.json")
    with open(copied_config, "r", encoding="utf-8") as f:
        config = json.load(f)
    assert config["dataSource"]["path"] == f"/data/{dataset_path.name}"


def test_update_config_with_html_names_infers_python_from_html(tmp_path) -> None:
    config_path = tmp_path / "dashboard_config.json"
    config_path.write_text(
        json.dumps(
            {
                "blocks": [
                    {
                        "id": "goal0_chart0",
                        "blockType": "view",
                        "blockContent": {
                            "html_code_name": "goal0_chart0_iteration2.html"
                        },
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    charts_dir = tmp_path / "charts"
    charts_dir.mkdir()
    (charts_dir / "goal0_chart0_echarts.py").write_text("def plot(df):\n    return None\n", encoding="utf-8")
    (charts_dir / "goal0_chart0_iteration2.html").write_text("<html></html>", encoding="utf-8")

    engineer = DashboardEngineer(llm_client=None, model="test-model")
    engineer._update_config_with_html_names(str(config_path), str(charts_dir))

    updated = json.loads(config_path.read_text(encoding="utf-8"))
    block_content = updated["blocks"][0]["blockContent"]
    assert block_content["python_code_name"] == "goal0_chart0_echarts.py"
    assert block_content["html_code_name"] == "goal0_chart0_iteration2.html"


def test_update_config_with_html_names_infers_python_from_block_id(tmp_path) -> None:
    config_path = tmp_path / "dashboard_config.json"
    config_path.write_text(
        json.dumps(
            {
                "blocks": [
                    {
                        "id": "goal2_chart0",
                        "blockType": "view",
                        "blockContent": {},
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    charts_dir = tmp_path / "charts"
    charts_dir.mkdir()
    (charts_dir / "goal2_chart0_echarts.py").write_text("def plot(df):\n    return None\n", encoding="utf-8")
    (charts_dir / "goal2_chart0_iteration1.html").write_text("<html></html>", encoding="utf-8")

    engineer = DashboardEngineer(llm_client=None, model="test-model")
    engineer._update_config_with_html_names(str(config_path), str(charts_dir))

    updated = json.loads(config_path.read_text(encoding="utf-8"))
    block_content = updated["blocks"][0]["blockContent"]
    assert block_content["python_code_name"] == "goal2_chart0_echarts.py"
    assert block_content["html_code_name"] == "goal2_chart0_iteration1.html"


def test_update_config_with_html_names_infers_python_from_intent_block_id(tmp_path) -> None:
    config_path = tmp_path / "dashboard_config.json"
    config_path.write_text(
        json.dumps(
            {
                "blocks": [
                    {
                        "id": "intent_0_goal_0_chart0",
                        "blockType": "view",
                        "blockContent": {},
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    charts_dir = tmp_path / "charts"
    charts_dir.mkdir()
    (charts_dir / "goal0_chart0_echarts.py").write_text("def plot(df):\n    return None\n", encoding="utf-8")
    (charts_dir / "goal0_chart0_iteration1.html").write_text("<html></html>", encoding="utf-8")

    engineer = DashboardEngineer(llm_client=None, model="test-model")
    engineer._update_config_with_html_names(str(config_path), str(charts_dir))

    updated = json.loads(config_path.read_text(encoding="utf-8"))
    block_content = updated["blocks"][0]["blockContent"]
    assert block_content["python_code_name"] == "goal0_chart0_echarts.py"
    assert block_content["html_code_name"] == "goal0_chart0_iteration1.html"


def test_process_dashboard_config_preserves_view_code_names(tmp_path, monkeypatch) -> None:
    dataset_path = tmp_path / "input.csv"
    dataset_path.write_text("city,region,marketing_budget\nHangzhou,East,100\n", encoding="utf-8")

    config_path = tmp_path / "dashboard_config.json"
    config_path.write_text(
        json.dumps(
            {
                "blocks": [
                    {
                        "id": "intent_0_goal_0_chart0",
                        "blockType": "view",
                        "blockContent": {
                            "python_code_name": "intent_0_goal_0_chart0_echarts.py",
                            "html_code_name": "intent_0_goal_0_chart0_iteration1.html",
                        },
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    va_app_path = tmp_path / "va_app"
    (va_app_path / "public" / "charts").mkdir(parents=True)
    (va_app_path / "public" / "charts" / "intent_0_goal_0_chart0_iteration1.html").write_text(
        '<div style="width: 1000px; height: 500px;"></div>',
        encoding="utf-8",
    )

    engineer = DashboardEngineer(
        llm_client=SimpleNamespace(
            generate=lambda *args, **kwargs: SimpleNamespace(
                content=json.dumps(
                    {
                        "blocks": [
                            {
                                "id": "intent_0_goal_0_chart0",
                                "blockType": "view",
                                "blockContent": {},
                            }
                        ]
                    }
                )
            )
        ),
        model="test-model",
    )

    engineer._process_dashboard_config(
        config_file_path=str(config_path),
        dataset_path=str(dataset_path),
        question="Show city performance",
        va_app_path=str(va_app_path),
        max_retries=1,
    )

    updated = json.loads(config_path.read_text(encoding="utf-8"))
    block_content = updated["blocks"][0]["blockContent"]
    assert block_content["python_code_name"] == "intent_0_goal_0_chart0_echarts.py"
    assert block_content["html_code_name"] == "intent_0_goal_0_chart0_iteration1.html"

import os

os.environ.setdefault("ALLOW_INSECURE_DEFAULTS", "true")
os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_BASE_URL", "http://localhost:8000")
os.environ.setdefault("LLM_MODEL", "test-model")

from app.deploy.services.video_naming import (
    expected_scene_component_files,
    extract_dataset_name_from_config,
    scene_id_to_filename,
    scene_needs_component_suffix,
)
from app.deploy.services.video import _build_scene_registry_ts


def test_extract_dataset_name_from_config_trims_special_chars_and_length() -> None:
    config = {"meta": {"title": "Exploring ART_AND_DESIGN Apps!!! 2026"}}

    assert extract_dataset_name_from_config(config) == "ExploringARTANDDESIG"


def test_scene_suffix_rules_cover_scene_type_and_legacy_name_patterns() -> None:
    assert scene_needs_component_suffix("scene_opening", "opening") is True
    assert scene_needs_component_suffix("summary_flight_statistics", None) is True
    assert scene_needs_component_suffix("analysis_carrier_delay", "chart") is False


def test_scene_id_to_filename_matches_expected_suffix_patterns() -> None:
    dataset_name = "FlightData"
    task_id = "task123"

    assert (
        scene_id_to_filename("scene_opening", dataset_name, task_id)
        == "FlightData_SceneOpening_task123ComponentAnimated.tsx"
    )
    assert (
        scene_id_to_filename("analysis_carrier_delay", dataset_name, task_id)
        == "FlightData_AnalysisCarrierDelay_task123Animated.tsx"
    )
    assert (
        scene_id_to_filename("summary_flight_statistics", dataset_name, task_id)
        == "FlightData_SummaryFlightStatistics_task123ComponentAnimated.tsx"
    )


def test_expected_scene_component_files_preserves_config_order() -> None:
    config = {
        "meta": {"title": "Flight Data"},
        "scenes": [
            {"id": "scene_opening", "type": "opening"},
            {"id": "analysis_carrier_delay", "type": "chart"},
            {"id": "summary_flight_statistics", "type": "stat_cards"},
            {"id": "scene_closing", "type": "closing"},
        ],
    }

    assert expected_scene_component_files(config, "task123") == {
        "scene_opening": "FlightData_SceneOpening_task123ComponentAnimated.tsx",
        "analysis_carrier_delay": "FlightData_AnalysisCarrierDelay_task123Animated.tsx",
        "summary_flight_statistics": "FlightData_SummaryFlightStatistics_task123ComponentAnimated.tsx",
        "scene_closing": "FlightData_SceneClosing_task123ComponentAnimated.tsx",
    }


def test_build_scene_registry_ts_uses_shared_expected_files() -> None:
    config = {
        "meta": {"title": "Flight Data"},
        "scenes": [
            {"id": "scene_opening", "type": "opening"},
            {"id": "analysis_carrier_delay", "type": "chart"},
        ],
    }

    registry_source = _build_scene_registry_ts(
        config,
        "task123",
        existing_files=set(expected_scene_component_files(config, "task123").values()),
    )

    assert "FlightData_SceneOpening_task123ComponentAnimated" in registry_source
    assert "FlightData_AnalysisCarrierDelay_task123Animated" in registry_source
    assert "'analysis_carrier_delay'" in registry_source

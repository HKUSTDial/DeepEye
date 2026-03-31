from __future__ import annotations

import unicodedata
from collections.abc import Mapping
from typing import Any

DEFAULT_DATASET_NAME = "DataAnalysis"
MAX_DATASET_NAME_LENGTH = 20


def dataset_name_from_title(
    title: str | None,
    fallback: str = DEFAULT_DATASET_NAME,
) -> str:
    cleaned = "".join(
        char
        for char in (title or "")
        if char.isalnum() or unicodedata.category(char).startswith("L")
    )
    trimmed = cleaned[:MAX_DATASET_NAME_LENGTH]
    return trimmed or fallback


def extract_dataset_name_from_config(
    config_data: Mapping[str, Any],
    fallback: str = DEFAULT_DATASET_NAME,
) -> str:
    meta = config_data.get("meta") or {}
    title = meta.get("title") if isinstance(meta, Mapping) else None
    return dataset_name_from_title(title if isinstance(title, str) else None, fallback=fallback)


def scene_needs_component_suffix(scene_id: str, scene_type: str | None = None) -> bool:
    if scene_type in {"opening", "closing", "stat_cards"}:
        return True
    return scene_id in {"scene_opening", "scene_closing"} or (
        "stat" in scene_id.lower() or scene_id.endswith("_statistics")
    )


def scene_id_to_filename(
    scene_id: str,
    dataset_name: str,
    task_id: str | None = None,
    *,
    is_animated: bool = True,
    needs_component: bool | None = None,
) -> str:
    scene_id_camel = "".join(word.capitalize() for word in scene_id.split("_"))
    needs_component_suffix = (
        scene_needs_component_suffix(scene_id)
        if needs_component is None
        else needs_component
    )

    if task_id:
        if is_animated:
            if needs_component_suffix:
                return f"{dataset_name}_{scene_id_camel}_{task_id}ComponentAnimated.tsx"
            return f"{dataset_name}_{scene_id_camel}_{task_id}Animated.tsx"
        if needs_component_suffix:
            return f"{dataset_name}_{scene_id_camel}_{task_id}Component.tsx"
        return f"{dataset_name}_{scene_id_camel}_{task_id}.tsx"

    if is_animated:
        if needs_component_suffix:
            return f"{dataset_name}_{scene_id_camel}ComponentAnimated.tsx"
        return f"{dataset_name}_{scene_id_camel}Animated.tsx"
    if needs_component_suffix:
        return f"{dataset_name}_{scene_id_camel}Component.tsx"
    return f"{dataset_name}_{scene_id_camel}.tsx"


def expected_scene_component_files(
    config_data: Mapping[str, Any],
    task_id: str,
    *,
    dataset_name: str | None = None,
) -> dict[str, str]:
    resolved_dataset_name = dataset_name or extract_dataset_name_from_config(config_data)
    expected_files: dict[str, str] = {}
    for scene in config_data.get("scenes") or []:
        if not isinstance(scene, Mapping):
            continue
        scene_id = scene.get("id")
        if not isinstance(scene_id, str) or not scene_id:
            continue
        scene_type = scene.get("type")
        expected_files[scene_id] = scene_id_to_filename(
            scene_id,
            resolved_dataset_name,
            task_id,
            is_animated=True,
            needs_component=scene_needs_component_suffix(
                scene_id,
                scene_type if isinstance(scene_type, str) else None,
            ),
        )
    return expected_files

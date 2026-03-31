from __future__ import annotations

import copy
import json
from typing import Any


def _normalize_indexed_items(value: Any) -> Any:
    if not isinstance(value, list):
        return value
    normalized: dict[str, Any] = {}
    for item in value:
        if not isinstance(item, dict):
            return value
        item_id = item.get("id")
        if not isinstance(item_id, str) or not item_id:
            return value
        normalized[item_id] = item
    return normalized


def _parse_json_object_string(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    text = value.strip()
    if not text or text[0] not in "{[":
        return value
    try:
        return json.loads(text)
    except Exception:
        return value


def _normalize_workflow_payload_shape(workflow: dict[str, Any] | str) -> dict[str, Any] | Any:
    workflow = _parse_json_object_string(workflow)
    if not isinstance(workflow, dict):
        return workflow
    normalized = copy.deepcopy(workflow)
    normalized["root"] = _parse_json_object_string(normalized.get("root"))
    root = normalized.get("root")
    if not isinstance(root, dict):
        return normalized
    root["nodes"] = _parse_json_object_string(root.get("nodes"))
    root["edges"] = _parse_json_object_string(root.get("edges"))
    root["nodes"] = _normalize_indexed_items(root.get("nodes"))
    root["edges"] = _normalize_indexed_items(root.get("edges"))
    return normalized

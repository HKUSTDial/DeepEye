"""Workflow template definitions and rendering."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


TEMPLATES = [
    {
        "id": "datasource_summary",
        "name": "File Datasource Profile",
        "description": "Read one attached file datasource and compute a lightweight profile.",
        "params": [
            {
                "key": "datasource_id",
                "required": True,
                "placeholder": "attached file datasource id",
            },
            {"key": "limit", "required": False, "default": 100},
        ],
        "definition": {
            "nodes": {
                "read": {
                    "id": "read",
                    "type": "datasource.read",
                    "params": {
                        "datasource_id": "{{datasource_id}}",
                        "limit": "{{limit}}",
                    },
                    "metadata": {"position": {"x": 120, "y": 120}},
                },
                "profile": {
                    "id": "profile",
                    "type": "rows.profile",
                    "params": {},
                    "metadata": {"position": {"x": 420, "y": 120}},
                },
            },
            "edges": {
                "e1": {
                    "id": "e1",
                    "source": {"node_id": "read", "port_id": "dataset_ref"},
                    "target": {"node_id": "profile", "port_id": "dataset_ref"},
                }
            },
        },
    }
]


def list_templates() -> list[dict]:
    return [
        {
            "id": template["id"],
            "name": template["name"],
            "description": template.get("description"),
            "params": template.get("params", []),
        }
        for template in TEMPLATES
    ]


def get_template(template_id: str) -> dict | None:
    for template in TEMPLATES:
        if template["id"] == template_id:
            return template
    return None


def render_template(definition: dict, params: dict[str, Any]) -> dict:
    data = deepcopy(definition)
    return _render_value(data, params)


def _render_value(value: Any, params: dict[str, Any]) -> Any:
    if isinstance(value, dict):
        return {key: _render_value(val, params) for key, val in value.items()}
    if isinstance(value, list):
        return [_render_value(item, params) for item in value]
    if isinstance(value, str) and value.startswith("{{") and value.endswith("}}"):
        key = value[2:-2].strip()
        return params.get(key)
    return value


def apply_defaults(template: dict, params: dict[str, Any]) -> dict[str, Any]:
    merged = dict(params or {})
    for param in template.get("params", []):
        key = param["key"]
        if key not in merged and "default" in param:
            merged[key] = param["default"]
    return merged


def validate_params(template: dict, params: dict[str, Any]) -> list[str]:
    missing: list[str] = []
    for param in template.get("params", []):
        if param.get("required") and not params.get(param["key"]):
            missing.append(param["key"])
    return missing

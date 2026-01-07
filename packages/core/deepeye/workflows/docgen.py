"""Generate markdown docs for registered node specs."""

from __future__ import annotations

from deepeye.workflows.examples import build_registry
from deepeye.workflows.registry import NodeSpec


def _render_port_table(ports: dict[str, object]) -> list[str]:
    if not ports:
        return ["(none)"]
    lines = ["| Port | Schema | Required | Multiple | Description |", "| --- | --- | --- | --- | --- |"]
    for port_id, port in ports.items():
        schema = getattr(port, "schema_", None)
        required = getattr(port, "required", False)
        multiple = getattr(port, "multiple", False)
        desc = getattr(port, "description", "") or ""
        lines.append(f"| `{port_id}` | `{schema}` | {required} | {multiple} | {desc} |")
    return lines


def render_markdown(specs: list[NodeSpec]) -> str:
    parts: list[str] = ["# Node Specifications", ""]
    for spec in specs:
        parts.append(f"## {spec.type}")
        if spec.description:
            parts.append(spec.description)
            parts.append("")
        parts.append("### Inputs")
        parts.extend(_render_port_table(spec.inputs))
        parts.append("")
        parts.append("### Outputs")
        parts.extend(_render_port_table(spec.outputs))
        parts.append("")
    return "\n".join(parts).rstrip() + "\n"


def main() -> None:
    registry = build_registry()
    markdown = render_markdown(registry.all())
    print(markdown)


if __name__ == "__main__":
    main()

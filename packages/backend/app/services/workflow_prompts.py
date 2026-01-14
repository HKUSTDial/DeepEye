from __future__ import annotations

from deepeye.workflows.registry import NodeRegistry, NodeSpec


def _render_port(port) -> str:
    schema = getattr(port, "schema_", None)
    required = getattr(port, "required", False)
    multiple = getattr(port, "multiple", False)
    parts = [f"schema={schema}", f"required={required}"]
    if multiple:
        parts.append("multiple=true")
    return ", ".join(parts)


def _render_params(params_schema: dict[str, object] | None) -> list[str]:
    if not params_schema:
        return []
    lines = []
    for key, meta in params_schema.items():
        if isinstance(meta, dict):
            meta_type = meta.get("type", "")
            required = meta.get("required", False)
            desc = meta.get("description", "")
            lines.append(f"- {key} ({meta_type}, required={required}) {desc}".strip())
        else:
            lines.append(f"- {key}: {meta}")
    return lines


def render_node_specs(specs: list[NodeSpec]) -> str:
    lines: list[str] = ["Node Specifications:"]
    for spec in specs:
        lines.append(f"* {spec.type}: {spec.description or ''}".rstrip())
        if spec.inputs:
            lines.append("  inputs:")
            for port_id, port in spec.inputs.items():
                lines.append(f"  - {port_id}: {_render_port(port)}")
        if spec.outputs:
            lines.append("  outputs:")
            for port_id, port in spec.outputs.items():
                lines.append(f"  - {port_id}: {_render_port(port)}")
        param_lines = _render_params(spec.params_schema or {})
        if param_lines:
            lines.append("  params:")
            lines.extend([f"  {line}" for line in param_lines])
    return "\n".join(lines).strip()


def _render_datasource_context(datasource: dict[str, str] | list[dict[str, str]] | None) -> str:
    if not datasource:
        return ""
    
    lines = ["Current datasource selections:"]
    ds_list = datasource if isinstance(datasource, list) else [datasource]
    
    for ds in ds_list:
        ds_id = ds.get('id', '')
        name = ds.get('name', '')
        dstype = ds.get('type', '')
        category = ds.get('category', 'database')
        
        lines.append(f"- id: {ds_id}")
        lines.append(f"  name: {name}")
        lines.append(f"  type: {dstype}")
        lines.append(f"  category: {category}")
        if category == "file":
            lines.append(f"  local_path: {ds.get('local_path', '')}")
            lines.append(f"  note: This file is already in the sandbox. Use python.code to read it.")
        else:
            lines.append(f"  note: Use this id in params.datasource_id for datasource.read or sql.execute.")
    
    return "\n".join(lines).strip()


def _render_schema_context(tables: list[dict[str, object]] | None) -> str:
    if not tables:
        return ""
    lines = ["Datasource schema/metadata overview:"]
    for table in tables:
        ds_name = table.get("datasource_name", "")
        name = table.get("name", "")
        kind = table.get("kind", "table")
        columns = table.get("columns", [])
        col_text = ", ".join(
            [
                f"{col.get('name', '')}:{col.get('type', '')}"
                for col in columns
                if isinstance(col, dict)
            ]
        )
        source_prefix = f"[{ds_name}] " if ds_name else ""
        lines.append(f"- {source_prefix}{name} ({kind}): {col_text}".strip())
        if kind == "file" and "preview" in table:
            lines.append(f"  preview: {table['preview']}")
    return "\n".join(lines).strip()


def build_workflow_prompt(
    registry: NodeRegistry,
    datasource: dict[str, str] | list[dict[str, str]] | None = None,
    tables: list[dict[str, object]] | None = None,
) -> str:
    specs_text = render_node_specs(registry.all())
    datasource_text = _render_datasource_context(datasource)
    schema_text = _render_schema_context(tables)
    return f"""You are a Workflow Designer for data analysis.
Your job is to translate a user's analysis goal into a JSON workflow definition.
You currently have a lean toolbox (primarily python.code) and should compose logic with it.

Rules (strict, structured JSON only):
0) First create a brief plan (2-4 steps) via create_plan before creating any workflow. Then execute the plan and call mark_step_done after each step. Use update_plan if the plan changes.
1) Use only node types and port ids from the specifications. Do NOT invent ports or node types.
2) Include every required input/output exactly as the spec defines (e.g., sql.execute.rows). If the spec defines an output, include it even if only one port is used.
3) Port multiplicity: only ports with `multiple=true` may have more than one incoming edge; all other inputs must have at most one incoming edge.
4) Keep the workflow minimal and logical. Do NOT call external agents (code_agent, sql_agent, etc.); all logic is workflow nodes (primarily python.code).
5) python.code inputs: the runner pipes ALL inputs as a JSON dict to stdin. Always read: `import sys, json; data = json.load(sys.stdin)` then access inputs as `data['input']`, `data['code']`, etc. Do not expect env vars. Code source: prefer params.code_path; code_b64 is allowed but avoid unless necessary; small snippets can use params.code. IMPORTANT: For outputs, prefer returning Python objects (e.g., list/dict) instead of printing JSON strings; downstream nodes receive structured data directly. Only parse with json.loads if the upstream output is explicitly a JSON string. For multi-line text output, use triple quotes (like '''...''') or f-strings to avoid JSON escape issues. Never write `print("` followed by a newline; Python will raise an unterminated string error. Use `\\n` or triple quotes instead.
6) Layout: include positions ONLY under node.metadata.position (x, y). Do NOT use a top-level "position" field.
7) Tool calls MUST be structured JSON frames (one object per call, no wrapping). Create the entire workflow in ONE call:
   - `create_workflow` payload: {{ "file_path": "...json", "workflow": {{ "root": {{ "nodes": {{...}}, "edges": {{...}} }} }} }}.
8) Reuse ONE workflow file for the whole task. If you need to iterate, call `read_workflow` and then `update_workflow` with the same file_path instead of creating new files.
9) You may run the workflow between updates to inspect outputs; keep edits minimal and only change what is required.
10) After creation or update, call `run_workflow_from_file` with payload {{ "file_path": "...json" }} to execute. Do NOT output bash commands.
11) Summarize the outputs concisely in the user's language.
12) Do NOT guess categorical values. Only use values explicitly provided by the user or datasource context; if unknown, omit instead of inventing.

Example (full workflow payload for create_workflow):
{{
  "file_path": "example.json",
  "workflow": {{
    "root": {{
      "nodes": {{
        "n1": {{
          "id": "n1",
          "type": "sql.execute",
          "inputs": {{}},
          "outputs": {{ "rows": {{ "schema": "list[dict]" }} }},
          "params": {{ "datasource_id": "<id>", "query": "SELECT 1" }},
          "metadata": {{ "position": {{ "x": 100, "y": 100 }} }}
        }},
        "n2": {{
          "id": "n2",
          "type": "python.code",
          "inputs": {{ "input": {{ "schema": "list[dict]", "required": true }} }},
          "outputs": {{ "stdout": {{ "schema": "string" }} }},
          "params": {{ "code": "import sys, json\nprint(json.load(sys.stdin))" }},
          "metadata": {{ "position": {{ "x": 320, "y": 100 }} }}
        }}
      }},
      "edges": {{
        "e1": {{
          "id": "e1",
          "source": {{ "node_id": "n1", "port_id": "rows" }},
          "target": {{ "node_id": "n2", "port_id": "input" }}
        }}
      }}
    }}
  }}
}}

Answer the user's question concisely based on the workflow outputs.

{datasource_text}

{schema_text}

{specs_text}
"""

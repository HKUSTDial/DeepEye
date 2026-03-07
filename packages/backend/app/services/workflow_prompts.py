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
            lines.append("  note: This file is already in the sandbox. Use this id in params.datasource_id for datasource.read.")
        else:
            lines.append("  note: Use this id in params.datasource_id for datasource.read or sql.execute.")
    
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
        preview = table.get("preview", [])
        col_text = ", ".join(
            [
                f"{col.get('name', '')}:{col.get('type', '')}"
                for col in columns
                if isinstance(col, dict)
            ]
        )
        source_prefix = f"[{ds_name}] " if ds_name else ""
        lines.append(f"- {source_prefix}{name} ({kind}): {col_text}".strip())
        if isinstance(preview, list) and preview:
            lines.append(f"  preview: {preview[:3]}")
    return "\n".join(lines).strip()


# Cap size of schema/datasource text to avoid context_length_exceeded (128k) with message history
_MAX_SCHEMA_CHARS = 12_000
_MAX_DATASOURCE_CHARS = 4_000


def _truncate(s: str, max_chars: int, suffix: str = "\n... (truncated for context limit)") -> str:
    if not s or len(s) <= max_chars:
        return s
    return s[: max_chars - len(suffix)] + suffix


def build_workflow_prompt(
    registry: NodeRegistry,
    datasource: dict[str, str] | list[dict[str, str]] | None = None,
    tables: list[dict[str, object]] | None = None,
) -> str:
    specs_text = render_node_specs(registry.all())
    datasource_text = _truncate(_render_datasource_context(datasource), _MAX_DATASOURCE_CHARS)
    schema_text = _truncate(_render_schema_context(tables), _MAX_SCHEMA_CHARS)
    return f"""You are a Workflow Designer for data analysis.
Your job is to translate a user's analysis goal into the smallest valid JSON workflow that can answer the request.
Prefer one-pass success over cleverness. Minimize tool calls, workflow edits, and repair loops.

Core planning priorities:
- Prefer specialized nodes over `python.code` whenever a specialized node cleanly fits the task.
- Use `rows.select`, `rows.filter`, `rows.sort`, `rows.aggregate`, and `rows.profile` for lightweight declarative transforms.
- Use `python.code` for multi-source joins, custom reshaping, non-trivial calculations, or logic that specialized nodes cannot express cleanly.
- For database-backed analysis, push filtering, aggregation, and projection into `sql.execute` before using downstream nodes.
- Use `dataset_ref` as the ONLY tabular data edge between workflow nodes. Do not connect `rows` ports between nodes.

Mandatory workflow construction rules:
1) Use only node types and exact port ids from the registry specification. Do NOT invent node types, ports, or schemas.
2) The registry spec is authoritative. `inputs` and `outputs` blocks are optional in workflow JSON. If you include them, they MUST match the registered spec exactly and must not invent extra ports.
3) Port multiplicity still applies: only ports with `multiple=true` may have more than one incoming edge.
4) If the task depends on attached files or databases, the workflow MUST include source nodes (`datasource.read` and/or `sql.execute`) before any transform, artifact, or answer nodes. Do NOT create python.code-only or llm.answer-only workflows for external data analysis tasks.
5) Use `llm.answer` for the final user-facing text answer grounded in workflow outputs.
6) For report requests, use `report.generate`.
7) For dashboard requests, use `data.generate_dashboard`.
8) For video requests, the workflow MUST end with `video.generator` receiving `dataset_ref`. The default simple pattern is `source -> video.generator`. Add transform nodes only when they materially change the dataset.
9) Layout: include positions ONLY under `node.metadata.position` with `x` and `y`. Do NOT use a top-level `position` field.
10) Do NOT guess categorical values, table names, or columns. Use only what the user, datasource context, or schema context provides.

Tool discipline:
1) For a new task, prefer `create_workflow_and_run` with the complete workflow.
2) Reuse ONE workflow draft for the whole task.
3) Do NOT call `read_workflow`, `update_workflow`, or `run_workflow` before the first run unless the user explicitly asks to edit or rerun an existing draft.
4) If `create_workflow_and_run` or `run_workflow` fails with `validation_errors` or `details`, do NOT reply yet. Reuse the SAME `draft_id`, fix only the reported issues, and run again. Limit repair attempts to 2.
5) After a successful run, do not keep editing the workflow. Summarize the outputs concisely in the user's language.
6) Treat `file_path` as legacy metadata only. Prefer draft-based execution.
7) Do NOT output bash commands.

High-frequency workflow patterns:
- Single attached file or database -> `datasource.read` or `sql.execute` -> optional `rows.*` / `python.code` -> `llm.answer`
- File + database joint analysis -> `datasource.read` + `sql.execute` -> `python.code` -> `llm.answer`
- Analysis report -> source node(s) -> optional transform -> `report.generate`
- Dashboard -> source node(s) -> optional transform -> `data.generate_dashboard`
- Data video -> source node(s) -> optional transform -> `video.generator`

Default planning heuristics:
- If the user asks for a single business answer such as "highest", "lowest", "top", "trend", "ratio", "distribution", or "which city/customer/product", default to a minimal answer workflow ending in `llm.answer`, not an artifact node.
- If both file and database sources are attached and the task requires joining or cross-source comparison, default to `datasource.read` + `sql.execute` + `python.code` + optional `llm.answer` / artifact node.
- If the user explicitly asks for a deliverable artifact (report, dashboard, video), end the workflow with that artifact node. Do not also add `llm.answer` unless the user also asked for a textual answer.
- Prefer one source node per datasource actually needed. Do not read every attached datasource if the task only needs one.
- If one SQL query can already produce the needed grouped or filtered result, prefer that over fetching raw rows into `python.code`.
- After a successful run, stop. Do not call `read_workflow` or `update_workflow` just to inspect or restate the same workflow.

python.code runtime contract:
- The runner only pipes LIGHTWEIGHT metadata to stdin. Always start with `import sys, json; data = json.load(sys.stdin)`.
- Use `data.get('input')` for small scalar or JSON parameters.
- For tabular data, use `data.get('dataset_ref', [])` and open each referenced sandbox path instead of expecting full rows in stdin.
- Never bypass source nodes by hardcoding attached datasource paths or database connections inside python.code. python.code should consume upstream `dataset_ref` inputs, not raw attached datasources.
- Prefer `params.code_path`; `code_b64` is allowed but should be avoided unless necessary; short snippets can use `params.code`.
- For small outputs, return normal Python objects. For large tabular outputs, write a dataset file in the sandbox and print a `dataset_ref` JSON object instead.
- For multi-line text, use triple quotes or explicit `\\n`. Never emit malformed Python strings.

Structured tool payloads:
- update_workflow: {{ "draft_id": "...", "workflow": {{ "root": {{ ... }} }} }}
- run_workflow: {{ "draft_id": "..." }}
- create_workflow_and_run: {{ "name": "analysis_workflow", "workflow": {{ "root": {{ ... }} }} }}

Answer the user's question concisely based on workflow outputs only.

{datasource_text}

{schema_text}

{specs_text}
"""

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
Your job is to translate a user's analysis goal into a JSON workflow definition.
You currently have a lean toolbox (primarily python.code) and should compose logic with it.

CRITICAL - For "生成数据视频" / "generate data video" goals use exactly 2 tool calls then reply:
1. create_plan  (steps e.g. ["Read CSV", "Generate video"])
2. create_workflow_and_run  (name e.g. "video", workflow with root.nodes and root.edges - datasource.read node + video.generator node + edge n1.rows→n2.rows)
3. Reply to user (only after create_workflow_and_run has returned)
Do NOT reply after only create_plan. You MUST call create_workflow_and_run with the full workflow JSON (two nodes + one edge). create_workflow_and_run creates or updates the workflow draft and runs it in one step.

Rules (strict, structured JSON only):
0) Follow the CRITICAL order above. For data video: create_plan then create_workflow_and_run then reply. Use update_plan if the plan changes.
0a) Do not reply until create_workflow_and_run has been called and returned. Never say "我已开始" or "我已完成" without having called create_workflow_and_run.
1) Use only node types and port ids from the specifications. Do NOT invent ports or node types.
2) The registry spec is authoritative. `inputs` / `outputs` blocks are optional in workflow JSON. If you include them, they MUST match the registered spec exactly and must not invent extra ports.
3) Port multiplicity: only ports with `multiple=true` may have more than one incoming edge; all other inputs must have at most one incoming edge.
4) Keep the workflow minimal and logical. PREFER specialized nodes over python.code when available:
   - For reading data from datasources: Use `datasource.read` node (outputs `rows: list[dict]`) instead of python.code
   - For video generation: Use `video.generator` node directly with `rows` from datasource.read and `query` from user input
   - For SQL queries: Use `sql.execute` node instead of python.code
   - Only use python.code when no specialized node exists for the task
5) VIDEO GENERATION WORKFLOW PATTERN (required when user asks for "data video" / "生成数据视频"):
   - You MUST create exactly TWO nodes and ONE edge. Never create only the data node without the video node.
   - For selected datasource (database OR file): Node 1 = `datasource.read` (params.datasource_id), Node 2 = `video.generator` (inputs.rows from n1, params.query from user goal). Edge: n1.rows → n2.rows.
6) python.code inputs: the runner pipes ALL inputs as a JSON dict to stdin. Always read: `import sys, json; data = json.load(sys.stdin)` then access inputs as `data['input']`, `data['code']`, etc. Do not expect env vars. Code source: prefer params.code_path; code_b64 is allowed but avoid unless necessary; small snippets can use params.code. IMPORTANT: For outputs, prefer returning Python objects (e.g., list/dict) instead of printing JSON strings; downstream nodes receive structured data directly. Only parse with json.loads if the upstream output is explicitly a JSON string. For multi-line text output, use triple quotes (like '''...''') or f-strings to avoid JSON escape issues. Never write `print("` followed by a newline; Python will raise an unterminated string error. Use `\\n` or triple quotes instead.
7) Layout: include positions ONLY under node.metadata.position (x, y). Do NOT use a top-level "position" field.
8) Tool calls MUST be structured JSON frames. Prefer workflow drafts over file paths:
   - create_workflow: {{ "name": "analysis_workflow", "workflow": {{ "root": {{ ... }} }} }} -> returns `draft_id`
   - update_workflow: {{ "draft_id": "...", "workflow": {{ "root": {{ ... }} }} }}
   - run_workflow: {{ "draft_id": "..." }}
   - create_workflow_and_run: {{ "name": "video", "workflow": {{ "root": {{ "nodes": {{...}}, "edges": {{...}} }} }} }}.
9) Reuse ONE workflow draft for the whole task. If you need to iterate, call `read_workflow` with the same `draft_id`, then `update_workflow` and `run_workflow`. Use `file_path` only when the user explicitly asks you to run a specific existing sandbox workflow file.
10) You may run the workflow between updates to inspect outputs; keep edits minimal and only change what is required.
11) After creation or update, you MUST call `run_workflow` with payload {{ "draft_id": "..." }} to execute. Only use `run_workflow_from_file` with {{ "file_path": "...json" }} for explicit legacy file-based workflows. Do NOT skip this step. Do NOT output bash commands.
12) Only after `run_workflow` or the explicit legacy fallback `run_workflow_from_file` returns, summarize the outputs concisely in the user's language. Do not claim the video is generated before running the workflow.
13) Do NOT guess categorical values. Only use values explicitly provided by the user or datasource context; if unknown, omit instead of inventing.

REPORT GENERATION (IMPORTANT):
When the user asks for a "report", "analysis report", "data report", "comprehensive analysis", 
"报告", "分析报告", "生成报告", or similar report-related requests, you MUST use the `report.generate` node:
- This node generates professional HTML reports with executive summary, KPIs, interactive charts, and recommendations.
- Required params: file_paths (list of CSV paths like ["/workspace/data/sales.csv"]) OR connect data input.
- Optional params: query (analysis focus), template ("template_0.html" or "template_1.html"), output_path.
- Example workflow for report generation:
  {{
    "nodes": {{
      "report": {{
        "id": "report",
        "type": "report.generate",
        "inputs": {{}},
        "outputs": {{ "report_path": {{ "schema": "string" }}, "status": {{ "schema": "string" }}, "message": {{ "schema": "string" }} }},
        "params": {{
          "file_paths": ["/workspace/data/your_data.csv"],
          "query": "Analyze sales trends and customer behavior",
          "template": "template_1.html"
        }},
        "metadata": {{ "position": {{ "x": 100, "y": 100 }} }}
      }}
    }},
    "edges": {{}}
  }}

Example 1 - Video Generation (SIMPLEST pattern):
{{
  "name": "video_example",
  "workflow": {{
    "root": {{
      "nodes": {{
        "n1": {{
          "id": "n1",
          "type": "datasource.read",
          "inputs": {{}},
          "outputs": {{ "rows": {{ "schema": "list[dict]" }} }},
          "params": {{ "datasource_id": "<datasource_id>" }},
          "metadata": {{ "position": {{ "x": 100, "y": 100 }} }}
        }},
        "n2": {{
          "id": "n2",
          "type": "video.generator",
          "inputs": {{
            "rows": {{ "schema": "list[dict]", "required": true }}
          }},
          "outputs": {{
            "video_path": {{ "schema": "string" }},
            "video_info": {{ "schema": "dict" }},
            "config": {{ "schema": "dict" }},
            "config_path": {{ "schema": "string" }}
          }},
          "params": {{
            "query": "请分析数据并生成包含可视化图表的中文视频",
            "language": "Chinese"
          }},
          "metadata": {{ "position": {{ "x": 320, "y": 100 }} }}
        }}
      }},
      "edges": {{
        "e1": {{
          "id": "e1",
          "source": {{ "node_id": "n1", "port_id": "rows" }},
          "target": {{ "node_id": "n2", "port_id": "rows" }}
        }}
      }}
    }}
  }}
}}
Note: For video.generator, set params.query from the user's goal (e.g. "分析航班延误数据并生成中文数据视频"). Always 2 nodes + 1 edge.

Example 2 - File datasource + video:
{{
  "name": "flight_video",
  "workflow": {{
    "root": {{
      "nodes": {{
        "n1": {{
          "id": "n1",
          "type": "datasource.read",
          "inputs": {{}},
          "outputs": {{ "rows": {{ "schema": "list[dict]" }} }},
          "params": {{ "datasource_id": "<file_datasource_id>" }},
          "metadata": {{ "position": {{ "x": 100, "y": 100 }} }}
        }},
        "n2": {{
          "id": "n2",
          "type": "video.generator",
          "inputs": {{ "rows": {{ "schema": "list[dict]", "required": true }}, "query": {{ "schema": "string", "required": true }} }},
          "outputs": {{ "video_path": {{ "schema": "string" }}, "video_info": {{ "schema": "dict" }}, "config": {{ "schema": "dict" }}, "config_path": {{ "schema": "string" }} }},
          "params": {{ "query": "Analyze the data and generate a Chinese data video with charts", "language": "Chinese" }},
          "metadata": {{ "position": {{ "x": 320, "y": 100 }} }}
        }}
      }},
      "edges": {{
        "e1": {{ "id": "e1", "source": {{ "node_id": "n1", "port_id": "rows" }}, "target": {{ "node_id": "n2", "port_id": "rows" }} }}
      }}
    }}
  }}
}}
Use datasource_id from datasource context. video.generator needs BOTH rows (from edge) and query (in params).

Example 3 - SQL Query:
{{
  "name": "sql_example",
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
        }}
      }},
      "edges": {{}}
    }}
  }}
}}

Answer the user's question concisely based on the workflow outputs.

{datasource_text}

{schema_text}

{specs_text}
"""

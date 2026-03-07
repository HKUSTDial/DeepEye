from __future__ import annotations

import base64
import json
from typing import Any

from app.node.core.base import BaseNode
from app.sandbox.docker_sandbox import DockerSandbox
from app.services.workflow_datasets import (
    compact_dataset_ref,
    compact_rows_preview,
    compact_value_for_transport,
    dataset_ref_columns,
    is_dataset_ref,
    build_tabular_node_result,
)
from deepeye.workflows.models import Node, Port
from deepeye.workflows.registry import NodeSpec


class PythonCodeHandler:
    def __init__(self, sandbox: DockerSandbox | None) -> None:
        self.sandbox = sandbox

    def _ensure_sandbox(self) -> DockerSandbox:
        if not self.sandbox or not getattr(self.sandbox, "container", None):
            raise RuntimeError("Sandbox not available for python.code node")
        return self.sandbox

    def _resolve_code(self, node: Node, inputs: dict[str, Any], container) -> str:
        code = inputs.get("code") or node.params.get("code")
        code_b64 = node.params.get("code_b64")
        code_path = node.params.get("code_path")

        if code_path:
            exit_code, output = container.exec_run(
                cmd=["bash", "-c", f"cat {code_path}"],
                demux=True,
                workdir="/workspace",
            )
            stdout = output[0].decode("utf-8") if output[0] else ""
            stderr = output[1].decode("utf-8") if output[1] else ""
            if exit_code != 0:
                raise RuntimeError(stderr or stdout or f"Failed to read code_path: {code_path}")
            code = stdout

        if not code and code_b64:
            try:
                code = base64.b64decode(code_b64).decode("utf-8")
            except Exception as exc:
                raise ValueError("Invalid code_b64; must be base64-encoded UTF-8 string") from exc

        if not code:
            raise ValueError("code is required (provide code, code_path, or code_b64)")
        return str(code)

    def _normalize_dataset_refs(self, value: Any) -> list[dict[str, Any]]:
        if is_dataset_ref(value):
            return [value]
        if isinstance(value, list):
            return [item for item in value if is_dataset_ref(item)]
        return []

    def _build_input_payload(self, node: Node, inputs: dict[str, Any]) -> dict[str, Any] | None:
        payload: dict[str, Any] = {}

        raw_input = inputs.get("input")
        if raw_input not in (None, "", [], {}):
            payload["input"] = compact_value_for_transport(raw_input, row_limit=10, text_limit=2000, list_limit=20)

        dataset_refs = self._normalize_dataset_refs(inputs.get("dataset_ref"))
        if dataset_refs:
            payload["dataset_ref"] = [compact_dataset_ref(item, preview_limit=10) for item in dataset_refs]

        return payload or None

    def execute(self, node: Node, inputs: dict[str, Any], context: object) -> dict[str, Any]:
        sandbox = self._ensure_sandbox()
        container = sandbox.container
        code = self._resolve_code(node, inputs, container)
        workdir = node.params.get("workdir") or "/workspace"

        safe_id = "".join(ch if str(ch).isalnum() or ch in ("-", "_") else "_" for ch in str(node.id)) or "script"
        script_path = f"/workspace/.workflow_scripts/{safe_id}.py"
        input_payload = self._build_input_payload(node, inputs)

        # Write user code
        full_code = code
        write_cmd = (
            f"mkdir -p /workspace/.workflow_scripts && "
            f"cat > {script_path} <<'PYCODE'\n{full_code}\nPYCODE"
        )
        exit_code, output = container.exec_run(
            cmd=["bash", "-c", write_cmd],
            demux=True,
            workdir="/workspace",
        )
        write_stdout = output[0].decode("utf-8") if output[0] else ""
        write_stderr = output[1].decode("utf-8") if output[1] else ""
        if exit_code != 0:
            raise RuntimeError(write_stderr or write_stdout or "failed to write python code")

        input_data = None
        # Prepare stdin file if payload exists
        input_redirect = ""
        if input_payload is not None:
            input_file = f"/workspace/.workflow_scripts/{safe_id}_input.json"
            input_data = json.dumps(input_payload, ensure_ascii=False, indent=2)
            write_input_cmd = f"cat > {input_file} <<'EOF'\n{input_data}\nEOF"
            exit_code, output = container.exec_run(
                cmd=["bash", "-c", write_input_cmd],
                demux=True,
                workdir="/workspace",
            )
            write_in_stdout = output[0].decode("utf-8") if output[0] else ""
            write_in_stderr = output[1].decode("utf-8") if output[1] else ""
            if exit_code != 0:
                raise RuntimeError(write_in_stderr or write_in_stdout or "failed to write python input")
            input_redirect = f" < {input_file}"

        run_cmd = ["bash", "-c", f"cd {workdir} && python {script_path}{input_redirect}"]
        exit_code, output = container.exec_run(
            cmd=run_cmd,
            demux=True,
            workdir="/workspace",
        )
        stdout = output[0].decode("utf-8") if output[0] else ""
        stderr = output[1].decode("utf-8") if output[1] else ""
        if exit_code != 0:
            if input_data:
                preview_lines = input_data.splitlines()[:10]
                preview = "\n".join(preview_lines)
                stderr = f"{stderr}\nINPUT_PREVIEW (first 10 lines):\n{preview}\n"
            else:
                stderr = f"{stderr}\nINPUT_PREVIEW: <empty>\n"
        result = {"stdout": stdout, "stderr": stderr, "exit_code": int(exit_code)}
        # Small tabular stdout is materialized into a dataset_ref for downstream workflow nodes.
        try:
            parsed = json.loads(stdout.strip())
            if isinstance(parsed, list) and all(isinstance(x, dict) for x in parsed):
                result.update(
                    build_tabular_node_result(
                        parsed,
                        sandbox=sandbox,
                        source="python.code",
                        name_hint=f"{safe_id}_output_rows",
                    )
                )
            elif is_dataset_ref(parsed):
                result["dataset_ref"] = parsed
                result["preview_rows"] = compact_rows_preview(parsed.get("preview_rows"), limit=20)
                result["columns"] = dataset_ref_columns(parsed)
                if parsed.get("row_count") is not None:
                    result["row_count"] = parsed.get("row_count")
        except (json.JSONDecodeError, TypeError):
            pass
        return result


class PythonCodeNode(BaseNode):
    node_type = "python.code"

    @classmethod
    def spec(cls) -> NodeSpec:
        return NodeSpec(
            type=cls.node_type,
            description="Execute custom Python code inside the sandbox. Use this for joins or custom transforms that specialized nodes cannot express cleanly.",
            params_schema={
                "code": {
                    "type": "string",
                    "required": True,
                    "description": "Python code to run. Read stdin with `data = json.load(sys.stdin)`, use `data.get('input')` for small parameters, and read tabular inputs from `data.get('dataset_ref', [])` paths inside the sandbox.",
                },
            },
            inputs={
                "input": Port(
                    schema="any",
                    required=False,
                    multiple=True,
                    description="Small JSON-serializable parameters passed to stdin as `data['input']`.",
                ),
                "dataset_ref": Port(
                    schema="dict",
                    required=False,
                    multiple=True,
                    description="Dataset reference(s). Read files from `data['dataset_ref'][i]['path']` inside the sandbox.",
                ),
            },
            outputs={
                "stdout": Port(schema="string", description="Standard output from the script."),
                "stderr": Port(schema="string", description="Standard error from the script."),
                "exit_code": Port(schema="int", description="Process exit code."),
                "preview_rows": Port(schema="list[dict]", required=False, description="Preview rows when the script returns tabular data."),
                "dataset_ref": Port(schema="dict", required=False, description="Returned dataset reference when the script materializes tabular output."),
                "row_count": Port(schema="int", required=False, description="Row count for the returned dataset, when available."),
                "columns": Port(schema="list[string]", required=False, description="Detected output columns when available."),
            },
        )

    @classmethod
    def build_handler(cls, db, user_id, sandbox=None):
        return PythonCodeHandler(sandbox)

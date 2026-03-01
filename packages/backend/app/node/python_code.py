from __future__ import annotations

import base64
import json
import json5
from typing import Any

from app.node.base import BaseNode
from app.sandbox.docker_sandbox import DockerSandbox
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

    def execute(self, node: Node, inputs: dict[str, Any], context: object) -> dict[str, Any]:
        sandbox = self._ensure_sandbox()
        container = sandbox.container
        code = self._resolve_code(node, inputs, container)
        workdir = node.params.get("workdir") or "/workspace"
        # Always pass the full inputs dict to stdin for consistency.
        # User code should read: data = json.load(sys.stdin)
        # and access inputs as data['input'], data['code'], etc.
        input_payload = inputs if inputs else None

        safe_id = "".join(ch if str(ch).isalnum() or ch in ("-", "_") else "_" for ch in str(node.id)) or "script"
        script_path = f"/workspace/.workflow_scripts/{safe_id}.py"

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
        # When stdout is a JSON array of objects, expose as rows for video.generator etc.
        try:
            parsed = json.loads(stdout.strip())
            if isinstance(parsed, list) and all(isinstance(x, dict) for x in parsed):
                result["rows"] = parsed
        except (json.JSONDecodeError, TypeError):
            pass
        return result


class PythonCodeNode(BaseNode):
    node_type = "python.code"

    @classmethod
    def spec(cls) -> NodeSpec:
        return NodeSpec(
            type=cls.node_type,
            description="Execute Python code inside the session sandbox (workdir defaults to /workspace). All inputs are passed as a JSON dict to stdin. Read with: data = json.load(sys.stdin), then access data['input'], data['code'], etc.",
            params_schema={
                "code": {"type": "string", "required": False, "description": "Python code snippet to run."},
                "code_path": {"type": "string", "required": False, "description": "Path inside sandbox to read code from (e.g., /workspace/script.py)."},
                "code_b64": {"type": "string", "required": False, "description": "Base64-encoded python code if escaping is an issue."},
                "workdir": {"type": "string", "required": False, "description": "Working directory inside sandbox."},
            },
            inputs={
                "input": Port(
                    schema="any",
                    required=False,
                    multiple=True,
                    description="Optional JSON-serializable input. Access in code as: data = json.load(sys.stdin); value = data['input']",
                ),
                "code": Port(schema="string", required=False, description="Optional code override passed via edge."),
            },
            outputs={
                "stdout": Port(schema="string", description="Standard output from the script."),
                "stderr": Port(schema="string", description="Standard error from the script."),
                "exit_code": Port(schema="int", description="Process exit code."),
                "rows": Port(
                    schema="list[dict]",
                    required=False,
                    description="Set when stdout is a JSON array of objects (e.g. print(df.to_json(orient='records'))). Use this to connect to video.generator.rows.",
                ),
            },
        )

    @classmethod
    def build_handler(cls, db, user_id, sandbox=None):
        return PythonCodeHandler(sandbox)

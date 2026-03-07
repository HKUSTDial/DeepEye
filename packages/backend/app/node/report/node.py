"""Report generation workflow node."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.node.core.base import BaseNode
from app.sandbox.docker_sandbox import DockerSandbox
from app.services.workflow_datasets import download_dataset_ref_to_local_csv, is_dataset_ref
from deepeye.workflows.models import Node, Port
from deepeye.workflows.registry import NodeSpec

from .runtime import create_report_temp_dir, run_report_pipeline

logger = logging.getLogger(__name__)


class ReportGenerateHandler:
    """Handler for report generation node execution."""

    def __init__(
        self,
        db: Session,
        user_id: str,
        sandbox: DockerSandbox | None = None,
        session_id: str | None = None,
    ) -> None:
        self.db = db
        self.user_id = user_id
        self.sandbox = sandbox
        self.session_id = session_id

    @staticmethod
    def _safe_csv_name(raw_name: str, fallback: str) -> str:
        clean = "".join(ch if ch.isalnum() or ch in ("-", "_", ".") else "_" for ch in raw_name)
        clean = clean.strip("._")
        if not clean:
            clean = fallback
        if not clean.lower().endswith(".csv"):
            clean = f"{clean}.csv"
        return clean

    @staticmethod
    def _normalize_file_paths(file_paths: Any) -> list[str]:
        if isinstance(file_paths, str):
            try:
                parsed = json.loads(file_paths)
                if isinstance(parsed, list):
                    file_paths = parsed
                else:
                    file_paths = [p.strip() for p in file_paths.split(",") if p.strip()]
            except json.JSONDecodeError:
                file_paths = [p.strip() for p in file_paths.split(",") if p.strip()]

        if not isinstance(file_paths, list):
            return []

        normalized: list[str] = []
        for item in file_paths:
            value = str(item).strip()
            if value:
                normalized.append(value)
        return normalized

    def _resolve_sandbox_paths(self, file_paths: list[str]) -> list[str]:
        resolved_paths = []
        for path in file_paths:
            if not path.startswith("/workspace"):
                path = f"/workspace/data/{path}"
            resolved_paths.append(path)
        return resolved_paths

    def _download_files_from_sandbox(
        self,
        file_paths: list[str],
        session_id: str | None = None,
        tmp_dir: str | None = None,
    ) -> tuple[list[str], str]:
        if not self.sandbox or not getattr(self.sandbox, "container", None):
            raise RuntimeError("Sandbox not available for report generation")

        tmp_dir = tmp_dir or create_report_temp_dir(session_id or self.session_id, prefix="deepeye_report_")
        local_paths: list[str] = []

        for idx, sandbox_path in enumerate(file_paths):
            exit_code, output = self.sandbox.container.exec_run(
                cmd=["cat", sandbox_path],
                demux=True,
                workdir="/workspace",
            )
            if exit_code != 0:
                stderr = output[1].decode("utf-8") if output and output[1] else ""
                raise RuntimeError(f"Failed to read file {sandbox_path}: {stderr}")

            content = output[0] if output and output[0] else b""
            source_name = Path(sandbox_path).name or f"input_{idx}.csv"
            filename = self._safe_csv_name(source_name, f"input_{idx}.csv")
            local_path = os.path.join(tmp_dir, f"{idx:02d}_{filename}")
            with open(local_path, "wb") as f:
                f.write(content)
            local_paths.append(local_path)
            logger.info("Downloaded %s to %s", sandbox_path, local_path)

        return local_paths, tmp_dir

    def _write_input_data_to_csv(self, input_data: Any, tmp_dir: str) -> list[str]:
        import pandas as pd

        csv_paths: list[str] = []
        if isinstance(input_data, list):
            df = pd.DataFrame(input_data)
            temp_csv = os.path.join(tmp_dir, "input_data.csv")
            df.to_csv(temp_csv, index=False)
            csv_paths.append(temp_csv)
            return csv_paths

        if isinstance(input_data, dict):
            for name, data in input_data.items():
                if not isinstance(data, list):
                    continue
                df = pd.DataFrame(data)
                safe_name = self._safe_csv_name(str(name), "table")
                temp_csv = os.path.join(tmp_dir, safe_name)
                df.to_csv(temp_csv, index=False)
                csv_paths.append(temp_csv)

        return csv_paths

    def execute(self, node: Node, inputs: dict[str, Any], context: object) -> dict[str, Any]:
        user_query = (
            node.params.get("query")
            or node.params.get("user_query")
            or "Generate a comprehensive data analysis report."
        )
        template_name = node.params.get("template") or node.params.get("template_name") or "template_1.html"
        output_filename = node.params.get("output_path") or node.params.get("output_filename") or "analysis_report.html"

        file_paths = self._normalize_file_paths(node.params.get("file_paths") or [])
        dataset_input = inputs.get("dataset_ref")
        dataset_refs = dataset_input if isinstance(dataset_input, list) else [dataset_input] if dataset_input else []
        dataset_refs = [ref for ref in dataset_refs if is_dataset_ref(ref)]
        if not file_paths and not dataset_refs:
            return {
                "report_path": "",
                "status": "error",
                "message": "No data source provided. Please specify file_paths in params or connect dataset_ref input.",
            }

        session_id = self.session_id or f"workflow_{self.user_id}"
        tmp_dir: str | None = None
        try:
            tmp_dir = create_report_temp_dir(session_id, prefix="deepeye_report_")
            local_paths: list[str] = []
            if file_paths:
                sandbox_paths = self._resolve_sandbox_paths(file_paths)
                copied_file_paths, _ = self._download_files_from_sandbox(sandbox_paths, session_id=session_id, tmp_dir=tmp_dir)
                local_paths.extend(copied_file_paths)
            for idx, dataset_ref in enumerate(dataset_refs):
                local_paths.append(
                    download_dataset_ref_to_local_csv(
                        dataset_ref,
                        sandbox=self.sandbox,
                        tmp_dir=tmp_dir,
                        name_hint=f"input_{idx}",
                    )
                )
            file_paths = local_paths

            if not file_paths:
                return {
                    "report_path": "",
                    "status": "error",
                    "message": "No valid CSV data found for report generation.",
                }

            logger.info("Starting report generation with query=%s, files=%s", user_query, file_paths)
            report_html, error = run_report_pipeline(
                session_id=session_id,
                user_query=user_query,
                csv_paths=file_paths,
                template_name=str(template_name),
                output_filename=str(output_filename),
            )
            if error:
                return {
                    "report_path": "",
                    "status": "error",
                    "message": f"Report generation failed: {error}",
                }

            return {
                "report_path": f"/workspace/{output_filename}",
                "status": "success",
                "message": f"Report generated successfully. Check {output_filename} in workspace.",
                "report_html": report_html[:500] + "..." if report_html and len(report_html) > 500 else report_html,
            }
        except Exception as exc:
            logger.exception("Report generation failed")
            return {
                "report_path": "",
                "status": "error",
                "message": f"Report generation error: {str(exc)}",
            }
        finally:
            if tmp_dir:
                import shutil

                try:
                    shutil.rmtree(tmp_dir, ignore_errors=True)
                except Exception:
                    pass


class ReportGenerateNode(BaseNode):
    """Workflow node for generating data analysis reports."""

    node_type = "report.generate"

    @classmethod
    def spec(cls) -> NodeSpec:
        return NodeSpec(
            type=cls.node_type,
            description=(
                "Generate a comprehensive data analysis report from CSV files. "
                "Use this node when the user asks for a 'report', 'analysis report', "
                "'data report', or wants a complete analysis with charts, KPIs, and insights. "
                "The report includes: executive summary, key metrics (KPIs), "
                "interactive charts, and business recommendations."
            ),
            params_schema={
                "file_paths": {
                    "type": "array",
                    "required": False,
                    "description": "List of CSV file paths in sandbox (e.g., ['/workspace/data/sales.csv']). Can also be comma-separated string.",
                },
                "query": {
                    "type": "string",
                    "required": False,
                    "description": "User's analysis query or focus area (e.g., 'Analyze sales trends and customer behavior'). Default: 'Generate a comprehensive data analysis report.'",
                },
                "template": {
                    "type": "string",
                    "required": False,
                    "description": "Report template name: 'template_0.html' (simple) or 'template_1.html' (detailed). Default: 'template_1.html'",
                },
                "output_path": {
                    "type": "string",
                    "required": False,
                    "description": "Output filename for the report (e.g., 'analysis_report.html'). Default: 'analysis_report.html'",
                },
            },
            inputs={
                "dataset_ref": Port(
                    schema="dict",
                    required=False,
                    multiple=True,
                    description="Optional dataset references from upstream nodes. Sandbox file paths will be consumed directly.",
                ),
            },
            outputs={
                "report_path": Port(
                    schema="string",
                    description="Path to the generated report file in sandbox.",
                ),
                "report_html": Port(
                    schema="string",
                    required=False,
                    description="HTML preview content of the generated report.",
                ),
                "status": Port(
                    schema="string",
                    description="Generation status: 'success' or 'error'.",
                ),
                "message": Port(
                    schema="string",
                    description="Status message with details.",
                ),
            },
        )

    @classmethod
    def build_handler(
        cls,
        db: Session,
        user_id: str,
        sandbox: DockerSandbox | None = None,
        session_id: str | None = None,
    ) -> ReportGenerateHandler:
        return ReportGenerateHandler(db, user_id, sandbox=sandbox, session_id=session_id)

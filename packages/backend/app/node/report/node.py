"""Report generation workflow node."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from app.node.core.base import BaseNode
from app.sandbox.docker_sandbox import DockerSandbox
from app.workflow.services.datasets import download_dataset_ref_to_local_csv, is_dataset_ref
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

    def execute(self, node: Node, inputs: dict[str, Any], context: object) -> dict[str, Any]:
        user_query = node.params.get("query")
        if not user_query:
            raise ValueError("query is required")
        template_name = "template_1.html"
        output_filename = "analysis_report.html"
        dataset_input = inputs.get("dataset_ref")
        dataset_refs = dataset_input if isinstance(dataset_input, list) else [dataset_input] if dataset_input else []
        dataset_refs = [ref for ref in dataset_refs if is_dataset_ref(ref)]
        if not dataset_refs:
            raise ValueError("dataset_ref input is required")

        session_id = self.session_id or f"workflow_{self.user_id}"
        tmp_dir: str | None = None
        try:
            tmp_dir = create_report_temp_dir(session_id, prefix="deepeye_report_")
            local_paths: list[str] = []
            for idx, dataset_ref in enumerate(dataset_refs):
                local_paths.append(
                    download_dataset_ref_to_local_csv(
                        dataset_ref,
                        sandbox=self.sandbox,
                        tmp_dir=tmp_dir,
                        name_hint=f"input_{idx}",
                )
            )
            if not local_paths:
                raise RuntimeError("No valid CSV data found for report generation.")

            logger.info("Starting report generation with query=%s, files=%s", user_query, local_paths)
            report_html, error = run_report_pipeline(
                session_id=session_id,
                user_query=user_query,
                csv_paths=local_paths,
                template_name=str(template_name),
                output_filename=str(output_filename),
            )
            if error:
                raise RuntimeError(f"Report generation failed: {error}")

            return {
                "report_path": f"/workspace/{output_filename}",
                "report_html": report_html,
            }
        except Exception as exc:
            logger.exception("Report generation failed")
            raise RuntimeError(f"Report generation error: {str(exc)}") from exc
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
                "Generate a comprehensive HTML data analysis report from one or more upstream datasets. "
                "Use this node when the user explicitly asks for a report deliverable."
            ),
            params_schema={
                "query": {
                    "type": "string",
                    "required": True,
                    "description": "Report focus or analysis question, such as 'Analyze revenue trends and customer behavior'.",
                },
            },
            inputs={
                "dataset_ref": Port(
                    schema="dict",
                    required=True,
                    multiple=True,
                    description="One or more dataset references to include in the report.",
                ),
            },
            outputs={
                "report_path": Port(
                    schema="string",
                    description="Sandbox path to the generated HTML report.",
                ),
                "report_html": Port(
                    schema="string",
                    required=False,
                    description="HTML preview snippet of the generated report.",
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

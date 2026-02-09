"""Report generation workflow node.

This node integrates report_module into the workflow engine,
allowing workflow agent to orchestrate report generation.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from typing import Any

from sqlalchemy.orm import Session

from app.node.base import BaseNode
from app.sandbox.docker_sandbox import DockerSandbox
from deepeye.workflows.models import Node, Port
from deepeye.workflows.registry import NodeSpec

logger = logging.getLogger(__name__)


class ReportGenerateHandler:
    """Handler for report generation node execution."""

    def __init__(self, db: Session, user_id: str, sandbox: DockerSandbox | None = None, session_id: str | None = None) -> None:
        self.db = db
        self.user_id = user_id
        self.sandbox = sandbox
        self.session_id = session_id

    def _get_file_paths_from_sandbox(self, file_paths: list[str]) -> list[str]:
        """Resolve file paths within the sandbox environment."""
        resolved_paths = []
        for path in file_paths:
            # If path doesn't start with /workspace, prepend it
            if not path.startswith("/workspace"):
                path = f"/workspace/data/{path}"
            resolved_paths.append(path)
        return resolved_paths

    def _download_files_from_sandbox(self, file_paths: list[str]) -> tuple[list[str], str]:
        """Download files from sandbox to temp directory for processing.
        
        Returns:
            tuple: (list of local file paths, temp directory path)
        """
        if not self.sandbox or not getattr(self.sandbox, "container", None):
            raise RuntimeError("Sandbox not available for report generation")

        tmp_dir = tempfile.mkdtemp(prefix="deepeye_report_")
        local_paths = []

        for sandbox_path in file_paths:
            # Read file from sandbox
            exit_code, output = self.sandbox.container.exec_run(
                cmd=["cat", sandbox_path],
                demux=True,
                workdir="/workspace",
            )
            if exit_code != 0:
                stderr = output[1].decode("utf-8") if output[1] else ""
                raise RuntimeError(f"Failed to read file {sandbox_path}: {stderr}")

            content = output[0] if output[0] else b""
            
            # Save to temp directory
            filename = os.path.basename(sandbox_path)
            local_path = os.path.join(tmp_dir, filename)
            with open(local_path, "wb") as f:
                f.write(content)
            local_paths.append(local_path)
            logger.info(f"Downloaded {sandbox_path} to {local_path}")

        return local_paths, tmp_dir

    def execute(self, node: Node, inputs: dict[str, Any], context: object) -> dict[str, Any]:
        """Execute report generation.
        
        Args:
            node: The workflow node definition
            inputs: Input data from connected nodes
            context: Execution context
            
        Returns:
            dict with keys: report_path, status, message
        """
        # Extract parameters
        user_query = node.params.get("query") or node.params.get("user_query") or "Generate a comprehensive data analysis report."
        template_name = node.params.get("template") or node.params.get("template_name") or "template_1.html"
        output_filename = node.params.get("output_path") or node.params.get("output_filename") or "analysis_report.html"
        
        # Get file paths from params or inputs
        file_paths = node.params.get("file_paths") or []
        if isinstance(file_paths, str):
            # Handle JSON string or comma-separated
            try:
                file_paths = json.loads(file_paths)
            except json.JSONDecodeError:
                file_paths = [p.strip() for p in file_paths.split(",") if p.strip()]
        
        # Also check for data input from connected nodes (e.g., datasource.read)
        input_data = inputs.get("data") or inputs.get("input")
        
        if not file_paths and not input_data:
            return {
                "report_path": "",
                "status": "error",
                "message": "No data source provided. Please specify file_paths in params or connect a data input.",
            }

        try:
            # Import report service here to avoid circular imports
            from app.services.report_service import run_report_pipeline
            from app.core.config import settings
            
            # If we have input data from connected nodes, save it to temp files
            tmp_dir = None
            if input_data and not file_paths:
                import pandas as pd
                tmp_dir = tempfile.mkdtemp(prefix="deepeye_report_input_")
                
                if isinstance(input_data, list):
                    # Assume it's a list of dicts (rows)
                    df = pd.DataFrame(input_data)
                    temp_csv = os.path.join(tmp_dir, "input_data.csv")
                    df.to_csv(temp_csv, index=False)
                    file_paths = [temp_csv]
                elif isinstance(input_data, dict):
                    # Could be multiple tables
                    for name, data in input_data.items():
                        if isinstance(data, list):
                            df = pd.DataFrame(data)
                            temp_csv = os.path.join(tmp_dir, f"{name}.csv")
                            df.to_csv(temp_csv, index=False)
                            file_paths.append(temp_csv)
            else:
                # Resolve sandbox paths and download files
                sandbox_paths = self._get_file_paths_from_sandbox(file_paths)
                file_paths, tmp_dir = self._download_files_from_sandbox(sandbox_paths)

            # Use session_id from handler or generate one
            session_id = self.session_id or f"workflow_{self.user_id}"
            
            # Run the report pipeline
            logger.info(f"Starting report generation with query: {user_query}, files: {file_paths}")
            report_html, error = run_report_pipeline(
                session_id=session_id,
                user_query=user_query,
                csv_paths=file_paths,
            )

            # Cleanup temp directory
            if tmp_dir:
                import shutil
                try:
                    shutil.rmtree(tmp_dir, ignore_errors=True)
                except Exception:
                    pass

            if error:
                return {
                    "report_path": "",
                    "status": "error",
                    "message": f"Report generation failed: {error}",
                }

            # The report is already saved to sandbox by report_service
            # Return success status
            return {
                "report_path": f"/workspace/{output_filename}",
                "status": "success",
                "message": f"Report generated successfully. Check {output_filename} in workspace.",
                "report_html": report_html[:500] + "..." if report_html and len(report_html) > 500 else report_html,
            }

        except Exception as e:
            logger.exception("Report generation failed")
            return {
                "report_path": "",
                "status": "error",
                "message": f"Report generation error: {str(e)}",
            }


class ReportGenerateNode(BaseNode):
    """Workflow node for generating data analysis reports.
    
    This node can be used by workflow agent to generate comprehensive
    data analysis reports from CSV files or data inputs.
    
    Usage:
        - Connect data from datasource.read or provide file_paths in params
        - Specify user_query to guide the analysis focus
        - The report will be saved to the sandbox workspace
    """
    
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
                "data": Port(
                    schema="any",
                    required=False,
                    multiple=True,
                    description="Optional data input from connected nodes (e.g., rows from datasource.read). If provided, will be converted to CSV for analysis.",
                ),
            },
            outputs={
                "report_path": Port(
                    schema="string",
                    description="Path to the generated report file in sandbox.",
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
    def build_handler(cls, db: Session, user_id: str, sandbox: DockerSandbox | None = None, session_id: str | None = None):
        return ReportGenerateHandler(db, user_id, sandbox=sandbox, session_id=session_id)

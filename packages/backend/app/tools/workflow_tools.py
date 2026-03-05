from __future__ import annotations

import json
import os
import re
import uuid
from typing import Annotated, List

from langchain_core.tools import InjectedToolCallId
from langchain_core.messages import ToolMessage
from langgraph.types import Command

from deepeye.tools.base import tool
from deepeye.tools.planning_tools import mark_step_done, update_plan
from app.db.session import SessionLocal
from app.repositories import SessionRepository
from app.services.workflow_file_service import service_run_workflow_from_file
from app.sandbox import sandbox_manager
from deepeye.agents import WorkflowAgent
from deepeye.utils.logger import logger

WORKFLOW_DIR = "/workspace/workflow"


def _get_session(db, session_id: str):
    try:
        session_uuid = uuid.UUID(session_id)
    except (TypeError, ValueError):
        logger.warning("[workflow_tools] Invalid session_id=%s", session_id)
        return None
    return SessionRepository(db).get(session_uuid)


def _sanitize_workflow_name(name: str) -> str:
    base = name.strip()
    if base.lower().endswith(".json"):
        base = base[:-5]
    clean = "".join(ch for ch in base if ch.isalnum() or ch in ("-", "_"))
    if not clean:
        clean = "workflow"
    return f"{clean}.json"


def _build_workflow_path(name: str) -> str:
    return f"{WORKFLOW_DIR}/{_sanitize_workflow_name(name)}"

@tool
def create_plan(
    steps: List[str],
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Annotated[Command, "The result of creating the plan"]:
    """Create a new execution plan with a list of steps. Example: [\"Query database\", \"Generate video\"]. After this you MUST call create_workflow then run_workflow_from_file before replying."""
    return Command(
        update={
            "plan": steps,
            "completed_steps": [],
            "messages": [
                ToolMessage(
                    content="Plan created. Next you MUST call create_workflow_and_run with file_path and workflow (root with nodes and edges). Do not reply until create_workflow_and_run has been called and returned.",
                    tool_call_id=tool_call_id,
                )
            ],
        }
    )


def _normalize_workflow_path(path: str) -> str:
    """Normalize path to always be under WORKFLOW_DIR."""
    if not isinstance(path, str):
        return path
    clean = path.strip()
    # Extract basename to ignore agent-provided subdirectories or wrong roots
    filename = os.path.basename(clean)
    return f"{WORKFLOW_DIR}/{_sanitize_workflow_name(filename)}"


async def _read_workflow_file(session_id: str, path: str) -> dict:
    sandbox = await sandbox_manager.get_or_create_sandbox(session_id)
    if not sandbox:
        raise ValueError("failed to get or create sandbox")
    result = await sandbox.exec_command(f"cat {path}")
    if result.exit_code != 0:
        raise ValueError(result.stderr or "failed to read workflow file")
    if not result.stdout.strip():
        raise ValueError("workflow file is empty")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid workflow json: {exc}") from exc


async def _write_workflow_path(session_id: str, path: str, data: dict) -> None:
    sandbox = await sandbox_manager.get_or_create_sandbox(session_id)
    if not sandbox:
        raise ValueError("failed to get or create sandbox")
    await sandbox.exec_command(f"mkdir -p {WORKFLOW_DIR}")
    payload = json.dumps(data, ensure_ascii=False, indent=2)
    result = await sandbox.exec_command(f"cat > {path} << 'EOF'\n{payload}\nEOF")
    if result.exit_code != 0:
        raise ValueError(result.stderr or "failed to write workflow file")


def create_create_workflow_tool(session_id: str) -> callable:
    @tool
    async def create_workflow(file_path: str, workflow: dict) -> dict:
        """
        Create or replace a full workflow JSON file.

        Args:
            file_path: Path to the workflow JSON file (e.g. student_count.json)
            workflow: The full workflow definition object
        """
        norm_path = _normalize_workflow_path(file_path)
        await _write_workflow_path(session_id, norm_path, workflow)
        return {"status": "success", "file_path": norm_path}

    return create_workflow


def create_read_workflow_tool(session_id: str) -> callable:
    @tool
    async def read_workflow(file_path: str) -> dict:
        """
        Read an existing workflow JSON file.

        Args:
            file_path: Path to the workflow JSON file
        """
        norm_path = _normalize_workflow_path(file_path)
        try:
            workflow = await _read_workflow_file(session_id, norm_path)
            return {"status": "success", "workflow": workflow, "file_path": norm_path}
        except Exception as exc:
            return {"status": "error", "error": str(exc), "file_path": norm_path}

    return read_workflow


def create_update_workflow_tool(session_id: str) -> callable:
    @tool
    async def update_workflow(file_path: str, workflow: dict) -> dict:
        """
        Update (overwrite) an existing workflow JSON file.

        Args:
            file_path: Path to the workflow JSON file
            workflow: The full workflow definition object
        """
        norm_path = _normalize_workflow_path(file_path)
        await _write_workflow_path(session_id, norm_path, workflow)
        return {"status": "success", "file_path": norm_path}

    return update_workflow


def _infer_language_from_query(query: str) -> str:
    """Infer narration language from query text: if contains CJK use Chinese, else English."""
    if not (query and query.strip()):
        return "English"
    for c in query:
        if "\u4e00" <= c <= "\u9fff" or "\u3040" <= c <= "\u30ff":
            return "Chinese"
    return "English"


def _build_data_video_workflow(datasource: dict, query: str) -> dict:
    """Build a 2-node workflow (data source → video.generator) for generate_data_video tool."""
    ds_id = datasource.get("id", "")
    category = datasource.get("category", "database")
    local_path = datasource.get("local_path", "")

    if category == "file" and local_path:
        # File: python.code reads CSV and outputs rows
        data_node = {
            "id": "n1",
            "type": "python.code",
            "inputs": {},
            "outputs": {"stdout": {"schema": "string"}, "rows": {"schema": "list[dict]"}},
            "params": {
                "code": f"import pandas as pd\ndf = pd.read_csv('{local_path}')\nprint(df.to_json(orient='records'))"
            },
            "metadata": {"position": {"x": 100, "y": 100}},
        }
    else:
        # Database: datasource.read
        data_node = {
            "id": "n1",
            "type": "datasource.read",
            "inputs": {},
            "outputs": {"rows": {"schema": "list[dict]"}},
            "params": {"datasource_id": ds_id},
            "metadata": {"position": {"x": 100, "y": 100}},
        }

    video_node = {
        "id": "n2",
        "type": "video.generator",
        "inputs": {"rows": {"schema": "list[dict]", "required": True}},
        "outputs": {
            "video_path": {"schema": "string"},
            "video_info": {"schema": "dict"},
            "config": {"schema": "dict"},
            "config_path": {"schema": "string"},
        },
        "params": {
            "query": query or "Analyze the data and generate a data video",
            "language": _infer_language_from_query(query or ""),
        },
        "metadata": {"position": {"x": 320, "y": 100}},
    }

    return {
        "root": {
            "nodes": {"n1": data_node, "n2": video_node},
            "edges": {
                "e1": {
                    "id": "e1",
                    "source": {"node_id": "n1", "port_id": "rows"},
                    "target": {"node_id": "n2", "port_id": "rows"},
                }
            },
        }
    }


def create_generate_data_video_tool(
    session_id: str,
    datasources_info: list[dict],
) -> callable:
    """
    One-shot tool for "生成数据视频": build workflow from current datasource, write and run.
    Same pattern as query_knowledge_base - one call, no sub-agent multi-step.
    """

    @tool
    async def generate_data_video(query: str = "Analyze the data and generate a data video") -> str:
        """
        Generate a data video from the currently selected data source. Call this when the user asks to generate a data video (生成数据视频 / generate data video). Uses the first selected datasource.
        Pass the user's goal in their own words and language: if they ask in English, use an English query; if in Chinese, use Chinese. Do not translate or rewrite into another language.
        """
        if not datasources_info:
            return "未选择数据源，请先在左侧选择或上传数据后再生成数据视频。"
        ds = datasources_info[0]
        workflow = _build_data_video_workflow(ds, query)
        path = f"{WORKFLOW_DIR}/data_video.json"
        await _write_workflow_path(session_id, path, workflow)
        db = SessionLocal()
        try:
            session = _get_session(db, session_id)
            if not session:
                return "Session not found."
            result = await service_run_workflow_from_file(db, session.user_id, session_id, path)
            status = result.get("status", "unknown")
            outputs = result.get("outputs", {}) or {}
            # 引擎可能返回 "success" 或 "finished"，都视为成功
            if status in ("finished", "success") and outputs:
                task_id = None
                for _nid, node_out in outputs.items():
                    if isinstance(node_out, dict):
                        vi = node_out.get("video_info") or {}
                        if vi.get("task_id"):
                            task_id = vi.get("task_id")
                            break
                        cfg_path = node_out.get("config_path") or ""
                        if "generated_" in cfg_path and "_aligned.json" in cfg_path:
                            m = re.search(r"generated_(\d{8}_\d{6})_aligned", cfg_path)
                            if m:
                                task_id = m.group(1)
                                break
                if task_id:
                    return f"数据视频已生成完成。流程：读取数据 → 生成配置与音频 → 渲染组件。Task ID：{task_id}。请在右侧 Video Preview 输入该 ID 加载预览。"
                return "数据视频已生成完成。流程：读取数据 → 生成配置与音频 → 渲染组件。请在右侧 Video Preview 查看。"
            if status not in ("finished", "success"):
                err = result.get("error", "")
                return f"运行结束状态: {status}。{err}"
            return "数据视频流程已执行。"
        finally:
            db.close()

    return generate_data_video


def create_run_workflow_from_file_tool(session_id: str) -> callable:
    @tool
    async def run_workflow_from_file(file_path: str) -> dict:
        """
        Run a workflow JSON from the sandbox file system.

        Args:
            file_path: Path to the workflow JSON file
        """
        norm_path = _normalize_workflow_path(file_path)
        db = SessionLocal()
        try:
            session = _get_session(db, session_id)
            if not session:
                return {"status": "error", "error": "Session not found."}
            result = await service_run_workflow_from_file(db, session.user_id, session_id, norm_path)
            return result
        finally:
            db.close()

    return run_workflow_from_file


def create_workflow_and_run_tool(session_id: str) -> callable:
    """Single tool: write workflow JSON and run it. Use this for data video so the agent cannot reply before running."""

    @tool
    async def create_workflow_and_run(file_path: str, workflow: dict) -> dict:
        """
        Create a workflow JSON file and run it immediately. Use this for data video generation in one step.
        Args:
            file_path: Path for the workflow JSON (e.g. video.json)
            workflow: Full workflow with root.nodes and root.edges
        """
        norm_path = _normalize_workflow_path(file_path)
        await _write_workflow_path(session_id, norm_path, workflow)
        db = SessionLocal()
        try:
            session = _get_session(db, session_id)
            if not session:
                return {"status": "error", "error": "Session not found."}
            result = await service_run_workflow_from_file(db, session.user_id, session_id, norm_path)
            return {"status": "success", "file_path": norm_path, "run": result}
        finally:
            db.close()

    return create_workflow_and_run


def create_generate_data_report_tool(session_id: str, datasources_info: list[dict]) -> callable:
    """
    One-shot tool for report generation: discovers CSV files from the sandbox,
    runs the report pipeline, and streams progress steps via Redis.
    Similar pattern to generate_data_video – one call, no sub-agent multi-step.
    """

    @tool
    async def generate_data_report(
        query: str = "Generate a comprehensive data analysis report.",
    ) -> str:
        """
        Generate a comprehensive data analysis report from the selected data sources.
        Call this when the user asks for a report, analysis report, 报告, 分析报告, or 数据报告.
        Pass the user's analysis goal as the query in their own language.
        Do NOT use the workflow agent for report generation – call this tool directly.
        """
        import asyncio
        import shutil

        from app.node.report.runtime import create_report_temp_dir, run_report_pipeline
        from app.sandbox.manager import SandboxManager

        # Collect sandbox CSV paths from selected datasources
        csv_sandbox_paths: list[str] = []
        for ds in datasources_info:
            if ds.get("category") == "file":
                lp = ds.get("local_path", "")
                if lp:
                    csv_sandbox_paths.append(lp)

        # Fallback: scan /workspace/data in the sandbox
        sandbox = await SandboxManager().get_or_create_sandbox(session_id)
        if not csv_sandbox_paths and sandbox:
            res = await sandbox.exec_command(
                "find /workspace/data -name '*.csv' 2>/dev/null"
            )
            if res.exit_code == 0 and res.stdout.strip():
                csv_sandbox_paths = [
                    p.strip() for p in res.stdout.strip().split("\n") if p.strip()
                ]

        if not csv_sandbox_paths:
            return "未找到 CSV 数据文件，请先在左侧上传数据文件后再生成报告。"

        if not sandbox or not getattr(sandbox, "container", None):
            return "无法访问沙箱容器，报告生成失败。"

        # Download files from sandbox to a host-side temp directory
        tmp_dir = create_report_temp_dir(session_id, prefix="deepeye_report_")
        csv_host_paths: list[str] = []
        try:
            for sp in csv_sandbox_paths:
                exit_code, output = sandbox.container.exec_run(
                    cmd=["cat", sp], demux=True, workdir="/workspace"
                )
                if exit_code != 0:
                    logger.warning("[generate_data_report] skip %s (exit %s)", sp, exit_code)
                    continue
                content: bytes = output[0] if output[0] else b""
                filename = os.path.basename(sp)
                local_path = os.path.join(tmp_dir, filename)
                with open(local_path, "wb") as f:
                    f.write(content)
                csv_host_paths.append(local_path)
                logger.info("[generate_data_report] downloaded %s → %s", sp, local_path)
        except Exception as exc:
            shutil.rmtree(tmp_dir, ignore_errors=True)
            return f"读取数据文件失败：{exc}"

        if not csv_host_paths:
            shutil.rmtree(tmp_dir, ignore_errors=True)
            return "无法从沙箱读取 CSV 文件，请检查数据是否已正确上传。"

        try:
            loop = asyncio.get_event_loop()
            _html, error = await loop.run_in_executor(
                None,
                lambda: run_report_pipeline(session_id, query, csv_host_paths),
            )
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

        if error:
            return f"Report generation failed: {error}"
        return "Report generation complete. View or download the HTML report in the right panel."

    return generate_data_report


def create_design_workflow_tool(model, session_id: str, system_prompt: str, callbacks: list | None = None) -> callable:
    @tool
    async def workflow_agent(goal: str) -> str:
        """
        Workflow Designer Agent: design, iterate, and run data analysis workflows.
        Pass a clear analysis goal and any relevant data context.
        """
        db = SessionLocal()
        try:
            session = _get_session(db, session_id)
            if not session:
                return "Session not found."
            workflow_agent_inst = WorkflowAgent(
                model=model,
                system_prompt=system_prompt,
                tools=[
                    create_plan,
                    update_plan,
                    mark_step_done,
                    create_workflow_and_run_tool(session_id),
                    create_create_workflow_tool(session_id),
                    create_read_workflow_tool(session_id),
                    create_update_workflow_tool(session_id),
                    create_run_workflow_from_file_tool(session_id),
                ],
            )
            result = await workflow_agent_inst.ainvoke(
                goal,
                thread_id=f"workflow_agent_{session_id}",
                config={"callbacks": callbacks},
            )
            messages = result.get("messages", [])
            return messages[-1].content if messages else ""
        finally:
            db.close()

    return workflow_agent

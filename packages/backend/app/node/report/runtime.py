"""Report runtime helpers: pipeline execution, temp workspace, and event publishing."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import tempfile
import threading
import traceback
from collections.abc import Coroutine
from datetime import datetime
from pathlib import Path

from app.core.config import get_report_session_root, settings
from app.sandbox.manager import SandboxManager
from app.workflow.events import build_workflow_artifact, publish_workflow_event_sync

from .report_module.pipeline import AutoReportPipeline

logger = logging.getLogger(__name__)

_ALLOWED_TEMPLATES = frozenset({"template_0.html", "template_1.html"})


def create_report_temp_dir(session_id: str | None, prefix: str = "deepeye_report_") -> str:
    """Create a report temp directory under report workspace root (session-scoped)."""
    base_dir = get_report_session_root(session_id)
    return tempfile.mkdtemp(prefix=prefix, dir=str(base_dir))


def create_report_temp_file(
    session_id: str | None,
    suffix: str = ".html",
    prefix: str = "deepeye_report_",
) -> str:
    """Create a report temp file under report workspace root (session-scoped)."""
    base_dir = get_report_session_root(session_id)
    fd, path = tempfile.mkstemp(suffix=suffix, prefix=prefix, dir=str(base_dir))
    os.close(fd)
    return path


def _publish_sync(channel: str, payload: dict) -> None:
    """Publish JSON payload to Redis (sync, for use from report thread)."""
    import redis

    redis_client = redis.Redis.from_url(settings.REDIS_URL)
    try:
        redis_client.publish(channel, json.dumps(payload))
    finally:
        redis_client.close()


def _run_coroutine_sync(coro: Coroutine[object, object, object]) -> None:
    """Run async coroutine from sync context, regardless of event-loop state."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        asyncio.run(coro)
        return

    error: Exception | None = None

    def _worker() -> None:
        nonlocal error
        try:
            asyncio.run(coro)
        except Exception as exc:  # pragma: no cover - delegated error path
            error = exc

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()
    thread.join()
    if error:
        raise error


def run_report_pipeline(
    session_id: str,
    user_query: str,
    csv_paths: list[str],
    template_name: str = "template_1.html",
    output_filename: str | None = None,
) -> tuple[str | None, str | None]:
    """Run report pipeline with CSV paths and user query.

    Returns:
        (report_html, error_message). On success error_message is None.
    """
    selected_template = template_name if template_name in _ALLOWED_TEMPLATES else "template_1.html"
    if selected_template != template_name:
        logger.warning(
            "[ReportRuntime] Unknown template '%s', fallback to '%s'",
            template_name,
            selected_template,
        )

    channel = f"session:{session_id}"
    out_path = create_report_temp_file(session_id, suffix=".html", prefix="deepeye_report_")
    steps_buffer: list[str] = []
    report_artifact = build_workflow_artifact("report")

    def _push_step(line: str) -> None:
        steps_buffer.append(line)
        publish_workflow_event_sync(
            channel,
            session_id,
            "artifact_progress",
            {
                "artifact": report_artifact,
                "message": line,
                "steps": steps_buffer,
            },
        )

    logger.info("[ReportRuntime] Starting report generation, output path: %s", out_path)
    try:
        pipeline = AutoReportPipeline(
            api_key=settings.LLM_API_KEY,
            base_url=settings.LLM_BASE_URL,
            model_name=settings.LLM_MODEL,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS,
            progress_callback=_push_step,
        )
        pipeline.run(
            csv_paths=csv_paths,
            user_query=user_query,
            template_name=selected_template,
            output_file=out_path,
        )

        logger.info("[ReportRuntime] Pipeline completed, checking output file: %s", out_path)
    except Exception as exc:
        error_detail = traceback.format_exc()
        logger.error("[ReportRuntime] Pipeline execution failed: %s", error_detail)
        _push_step(f"❌ Error: {exc}")
        publish_workflow_event_sync(
            channel,
            session_id,
            "artifact_failed",
            {
                "artifact": report_artifact,
                "steps": steps_buffer,
                "error": str(exc),
            },
        )
        return None, error_detail

    report_html = ""
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    safe_session = session_id.replace("-", "")
    if output_filename:
        candidate = Path(output_filename).name.strip()
        candidate = "".join(ch if ch.isalnum() or ch in ("-", "_", ".") else "_" for ch in candidate)
        candidate = candidate.strip("._")
        if candidate and not candidate.lower().endswith(".html"):
            candidate = f"{candidate}.html"
        report_filename = candidate or f"report_{safe_session}_{timestamp}.html"
    else:
        report_filename = f"report_{safe_session}_{timestamp}.html"

    abs_out_path = os.path.abspath(out_path)
    logger.info(
        "[ReportRuntime] Checking output file: %s, exists: %s",
        abs_out_path,
        os.path.exists(abs_out_path),
    )
    if os.path.exists(abs_out_path):
        try:
            with open(abs_out_path, "r", encoding="utf-8") as f:
                report_html = f.read()
            logger.info("[ReportRuntime] Read report HTML, length=%s", len(report_html))
        except Exception as exc:
            logger.error("[ReportRuntime] Failed to read report HTML from %s: %s", abs_out_path, exc)
            return None, f"Failed to read generated report: {exc}"

        if report_html:
            try:

                async def _write_report_to_sandbox() -> None:
                    manager = SandboxManager()
                    sandbox = await manager.get_or_create_sandbox(session_id)
                    if sandbox is None:
                        logger.warning("[ReportRuntime] No sandbox available for report save")
                        return
                    dest_path = f"/workspace/{report_filename}"
                    await sandbox.write_file(dest_path, report_html.encode("utf-8"))
                    logger.info("[ReportRuntime] Saved report to sandbox: %s", dest_path)

                _run_coroutine_sync(_write_report_to_sandbox())

                from app.schemas.events import SandboxEventType

                _publish_sync(
                    channel,
                    {
                        "type": SandboxEventType.FILES_CHANGED.value,
                        "source": "report",
                        "content": f"Report saved to workspace: {report_filename}",
                    },
                )
            except Exception as exc:
                logger.warning("[ReportRuntime] Failed to save report to sandbox: %s", exc)

        try:
            os.unlink(abs_out_path)
        except OSError:
            pass
    else:
        logger.error("[ReportRuntime] Output file does not exist: %s", abs_out_path)
        try:
            out_dir = Path(abs_out_path).parent
            tmp_files = [f.name for f in out_dir.glob("deepeye_report_*")]
            logger.info(
                "[ReportRuntime] Found %d report temp files in %s: %s",
                len(tmp_files),
                out_dir,
                tmp_files[:5],
            )
        except Exception:
            pass
        return None, f"Report output file not found: {abs_out_path}"

    if not report_html:
        logger.error("[ReportRuntime] Report HTML is empty")
        return None, "Generated report is empty"

    logger.info("[ReportRuntime] Publishing report artifact with %d bytes", len(report_html))
    publish_workflow_event_sync(
        channel,
        session_id,
        "artifact_ready",
        {
            "artifact": build_workflow_artifact(
                "report",
                report_path=f"/workspace/{report_filename}",
                report_filename=report_filename,
                report_html=report_html,
            ),
            "steps": steps_buffer,
            "report_html": report_html,
            "report_filename": report_filename,
        },
    )
    return report_html, None


def run_report_in_thread(
    session_id: str,
    user_query: str,
    csv_paths: list[str],
    template_name: str = "template_1.html",
    tmp_dir: str | None = None,
) -> None:
    """Run report pipeline in a background thread."""
    import shutil

    def work() -> None:
        try:
            run_report_pipeline(session_id, user_query, csv_paths, template_name=template_name)
        finally:
            if tmp_dir:
                try:
                    shutil.rmtree(tmp_dir, ignore_errors=True)
                except Exception:
                    pass

    thread = threading.Thread(target=work, daemon=True)
    thread.start()

"""Report generation service: runs report_module pipeline and publishes steps to Redis."""

from __future__ import annotations

import json
import logging
import os
import sys
import tempfile
import threading
from datetime import datetime
from pathlib import Path

from app.core.config import settings
from app.sandbox.manager import SandboxManager

logger = logging.getLogger(__name__)

# Paths used when loading report_module (do not import pipeline at module level)
_THIS_DIR = Path(__file__).resolve().parent
_SHIM_DIR = _THIS_DIR / "report_compat_shim"
_WORKSPACE_DIR = _THIS_DIR / "report_workspace"
# Project root (DeepEye-1) containing report_module: services->app->backend->packages->root
_PROJECT_ROOT = _THIS_DIR.resolve().parents[3]
_REPORT_MODULE_DIR = _PROJECT_ROOT / "report_module"


def _publish_sync(channel: str, payload: dict) -> None:
    """Publish JSON payload to Redis (sync, for use from report thread)."""
    import redis
    r = redis.Redis.from_url(settings.REDIS_URL)
    try:
        r.publish(channel, json.dumps(payload))
    finally:
        r.close()


def run_report_pipeline(
    session_id: str,
    user_query: str,
    csv_paths: list[str],
) -> tuple[str | None, str | None]:
    """Run report_module pipeline with CSV paths and user query.

    Does not modify report_module. Injects compat utils and redirects stdout
    so each printed line is published to Redis as report_step.

    Returns (report_html, error_message). On success error_message is None.
    """
    channel = f"session:{session_id}"
    out_path = tempfile.mktemp(suffix=".html", prefix="deepeye_report_")
    steps_buffer: list[str] = []

    class StdoutForward:
        def __init__(self, original: object):
            self._original = original

        def write(self, text: str) -> None:
            if not text:
                return
            lines = text.rstrip("\n").split("\n")
            for line in lines:
                if line.strip():
                    steps_buffer.append(line)
                    _publish_sync(channel, {"type": "report_step", "source": "report", "content": line})

        def flush(self) -> None:
            if hasattr(self._original, "flush"):
                self._original.flush()  # type: ignore[misc]

    old_stdout = sys.stdout
    old_cwd = os.getcwd()
    logger.info(f"[ReportService] Starting report generation, output path: {out_path}")
    try:
        # Resolve report_module imports: utils (shim), report_module package, config/DatasetContextGenerator (report_module dir)
        sys.path.insert(0, str(_SHIM_DIR))
        sys.path.insert(0, str(_PROJECT_ROOT))
        if _REPORT_MODULE_DIR.is_dir():
            sys.path.insert(0, str(_REPORT_MODULE_DIR))
        sys.stdout = StdoutForward(old_stdout)  # type: ignore[assignment]
        os.chdir(str(_WORKSPACE_DIR))

        from report_module.pipeline import AutoReportPipeline

        pipeline = AutoReportPipeline(
            api_key=settings.LLM_API_KEY,
            base_url=settings.LLM_BASE_URL,
        )
        pipeline.run(
            csv_paths=csv_paths,
            user_query=user_query,
            template_name="template_1.html",
            output_file=out_path,
        )
        logger.info(f"[ReportService] Pipeline.run() completed, checking output file: {out_path}")
    except Exception as e:
        import traceback
        err = traceback.format_exc()
        logger.error(f"[ReportService] Pipeline execution failed: {err}")
        _publish_sync(channel, {"type": "report_step", "source": "report", "content": f"❌ Error: {e}"})
        # Send report_done with error so frontend knows generation failed
        _publish_sync(channel, {
            "type": "report_done",
            "source": "report",
            "data": {"report_html": None, "steps": steps_buffer, "error": str(e)},
        })
        return None, err
    finally:
        sys.stdout = old_stdout
        os.chdir(old_cwd)
        # Remove our path entries to avoid affecting other code
        for path_entry in (str(_REPORT_MODULE_DIR), str(_PROJECT_ROOT), str(_SHIM_DIR)):
            try:
                sys.path.remove(path_entry)
            except ValueError:
                pass

    report_html = ""
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    safe_session = session_id.replace("-", "")
    report_filename = f"report_{safe_session}_{timestamp}.html"
    
    # Check if file exists (use absolute path to be safe)
    abs_out_path = os.path.abspath(out_path)
    logger.info(f"[ReportService] Checking for output file: {abs_out_path}, exists: {os.path.exists(abs_out_path)}")
    if os.path.exists(abs_out_path):
        try:
            with open(abs_out_path, "r", encoding="utf-8") as f:
                report_html = f.read()
            logger.info(f"[ReportService] Successfully read report HTML, length: {len(report_html)}")
        except Exception as e:
            logger.error(f"[ReportService] Failed to read report HTML from {abs_out_path}: {e}")
            return None, f"Failed to read generated report: {e}"

        # Persist a copy of the report HTML into the user's sandbox so it shows up
        # under the Files panel (`/workspace/...html`), directly in the workspace root.
        if report_html:
            try:
                async def _write_report_to_sandbox() -> None:
                    manager = SandboxManager()
                    sandbox = await manager.get_or_create_sandbox(session_id)
                    if sandbox is None:
                        logger.warning("[ReportService] No sandbox available for report save")
                        return
                    # Save directly in /workspace/ (same level as /workspace/data/)
                    dest_path = f"/workspace/{report_filename}"
                    await sandbox.write_file(dest_path, report_html.encode("utf-8"))
                    logger.info(f"[ReportService] Saved report to sandbox: {dest_path}")

                import asyncio

                asyncio.run(_write_report_to_sandbox())
                
                # Notify frontend to refresh Files panel so user can see the new report
                from app.schemas.events import SandboxEventType
                _publish_sync(channel, {
                    "type": SandboxEventType.FILES_CHANGED.value,
                    "source": "report",
                    "content": f"Report saved to workspace: {report_filename}"
                })
            except Exception as e:
                # Persistence errors should not break the report flow
                logger.warning(f"[ReportService] Failed to save report to sandbox: {e}")

        try:
            os.unlink(abs_out_path)
        except OSError:
            pass
    else:
        logger.error(f"[ReportService] Output file does not exist: {abs_out_path}")
        # List files in /tmp to help debug
        try:
            tmp_files = [f for f in os.listdir("/tmp") if f.startswith("deepeye_report_")]
            logger.info(f"[ReportService] Found {len(tmp_files)} deepeye report files in /tmp: {tmp_files[:5]}")
        except:
            pass
        return None, f"Report output file not found: {abs_out_path}"

    if not report_html:
        logger.error("[ReportService] Report HTML is empty")
        return None, "Generated report is empty"
    
    logger.info(f"[ReportService] Sending report_done event with {len(report_html)} bytes")
    _publish_sync(channel, {
        "type": "report_done",
        "source": "report",
        "data": {
            "report_html": report_html, 
            "steps": steps_buffer,
            "report_filename": report_filename,
        },
    })
    return report_html, None


def run_report_in_thread(
    session_id: str,
    user_query: str,
    csv_paths: list[str],
    tmp_dir: str | None = None,
) -> None:
    """Run report pipeline in a background thread and send agent_start/agent_end via Redis."""
    import shutil
    channel = f"session:{session_id}"
    _publish_sync(channel, {"type": "agent_start", "source": "report"})

    def work() -> None:
        try:
            run_report_pipeline(session_id, user_query, csv_paths)
        finally:
            _publish_sync(channel, {"type": "agent_end", "source": "report"})
            if tmp_dir:
                try:
                    shutil.rmtree(tmp_dir, ignore_errors=True)
                except Exception:
                    pass

    t = threading.Thread(target=work, daemon=True)
    t.start()

"""Report generation API: upload CSV(s) + query, run report pipeline, stream steps via SSE."""

import logging
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.node.report.runtime import create_report_temp_dir, run_report_in_thread
from app.schemas import UserMessage
from app.tasks.callbacks import persist_message

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/report", tags=["report"])


def _safe_csv_filename(raw_name: str, fallback: str = "upload.csv") -> str:
    base = Path(raw_name).name.strip()
    clean = "".join(ch if ch.isalnum() or ch in ("-", "_", ".") else "_" for ch in base)
    clean = clean.strip("._") or fallback
    if not clean.lower().endswith(".csv"):
        clean = f"{clean}.csv"
    return clean


@router.post("/generate")
async def generate_report(
    session_id: str = Form(...),
    message: str = Form(default=""),
    template_name: str = Form(default="template_1.html"),
    files: list[UploadFile] = File(..., description="One or more CSV files"),
):
    """Start report generation: CSV files + user query. Steps stream on session SSE."""
    if not files:
        raise HTTPException(status_code=422, detail="At least one CSV file is required")
    if not session_id or session_id == "draft":
        raise HTTPException(
            status_code=400,
            detail="Invalid session. Please create or select a conversation first (send a message without files, or refresh and try again).",
        )
    csv_paths = []
    tmp_dir = create_report_temp_dir(session_id, prefix="deepeye_report_")
    try:
        for f in files:
            if not f.filename or not f.filename.lower().endswith(".csv"):
                continue
            safe_name = _safe_csv_filename(f.filename or "upload.csv")
            path = Path(tmp_dir) / safe_name
            content = await f.read()
            path.write_bytes(content)
            csv_paths.append(str(path))
        if not csv_paths:
            raise HTTPException(status_code=422, detail="No valid CSV files")
        query = (message or "").strip() or "Generate a comprehensive report."
        try:
            persist_message(session_id, UserMessage(content=query))
        except Exception as e:
            logger.warning("Report: persist_message failed (report will still run): %s", e)
        run_report_in_thread(
            session_id,
            query,
            csv_paths,
            template_name=template_name,
            tmp_dir=tmp_dir,
        )
        return {"session_id": session_id, "message": "Report generation started. Connect to session SSE for progress."}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Report generate failed")
        raise HTTPException(status_code=500, detail=f"Report failed: {str(e)}")

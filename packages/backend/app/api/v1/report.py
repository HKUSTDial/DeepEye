"""Report generation API: upload tabular files + query, run report pipeline, stream steps via SSE."""

import io
import json
import logging
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
import pandas as pd

from app.node.report.runtime import create_report_temp_dir, run_report_in_thread
from app.services.datasource_specs import ensure_supported_filename, sanitize_filename
from app.schemas import UserMessage
from app.tasks.callbacks import persist_message

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/report", tags=["report"])


def _read_tabular_file_as_df(filename: str, data: bytes) -> pd.DataFrame:
    file_type = ensure_supported_filename(filename)
    if file_type == "csv":
        return pd.read_csv(io.BytesIO(data))
    if file_type in {"xlsx", "xls"}:
        return pd.read_excel(io.BytesIO(data))
    if file_type == "json":
        try:
            return pd.read_json(io.BytesIO(data), lines=True)
        except ValueError:
            payload = json.loads(data.decode("utf-8"))
            if isinstance(payload, list):
                return pd.DataFrame(payload)
            return pd.DataFrame([payload])
    if file_type == "parquet":
        return pd.read_parquet(io.BytesIO(data))
    raise ValueError(f"Unsupported file type: {file_type}")


@router.post("/generate")
async def generate_report(
    session_id: str = Form(...),
    message: str = Form(default=""),
    template_name: str = Form(default="template_1.html"),
    files: list[UploadFile] = File(..., description="One or more data files (csv/json/xlsx/xls/parquet)"),
):
    """Start report generation: tabular files + user query. Steps stream on session SSE."""
    if not files:
        raise HTTPException(status_code=422, detail="At least one data file is required")
    if not session_id or session_id == "draft":
        raise HTTPException(
            status_code=400,
            detail="Invalid session. Please create or select a conversation first (send a message without files, or refresh and try again).",
        )
    csv_paths = []
    tmp_dir = create_report_temp_dir(session_id, prefix="deepeye_report_")
    try:
        for idx, f in enumerate(files):
            if not f.filename:
                continue
            content = await f.read()
            try:
                df = _read_tabular_file_as_df(f.filename, content)
            except Exception:
                continue
            safe_stem = Path(sanitize_filename(f.filename, fallback="upload")).stem or "upload"
            path = Path(tmp_dir) / f"{idx + 1}_{safe_stem}.csv"
            df.to_csv(path, index=False)
            csv_paths.append(str(path))
        if not csv_paths:
            raise HTTPException(status_code=422, detail="No valid supported data files")
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

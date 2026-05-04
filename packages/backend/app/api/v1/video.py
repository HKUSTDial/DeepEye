"""Video asset APIs (authenticated, session-scoped)."""

from __future__ import annotations

import json
import re
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response
from fastapi.responses import FileResponse, PlainTextResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import get_video_session_root, normalize_session_id
from app.core.deps import CurrentUserId
from app.db.session import get_db
from app.repositories import SessionRepository
from app.deploy.services.video_naming import expected_scene_component_files
from deepeye.utils.logger import logger

router = APIRouter(prefix="/video", tags=["video"])

_TASK_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{6,128}$")
_CONTAINER_PATTERN = re.compile(r"^deepeye-video-([A-Za-z0-9._-]{6,128})$")


def _resolve_session_id_or_400(session_id: str | None) -> str | None:
    try:
        return normalize_session_id(session_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _require_owned_session_id(
    session_id: str | None,
    user_id: uuid.UUID,
    db: Session,
) -> str:
    normalized_session_id = _resolve_session_id_or_400(session_id)
    if not normalized_session_id:
        raise HTTPException(status_code=400, detail="session_id is required")
    try:
        session_uuid = uuid.UUID(normalized_session_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid session_id format") from exc
    owned = SessionRepository(db).get_by_id_and_user(session_uuid, user_id)
    if not owned:
        raise HTTPException(status_code=404, detail="Session not found")
    return normalized_session_id


def _validate_task_id_or_400(task_id: str) -> str:
    value = (task_id or "").strip()
    if not value or not _TASK_ID_PATTERN.fullmatch(value):
        raise HTTPException(status_code=400, detail="Invalid task_id")
    return value


def _video_dirs(session_id: str) -> tuple[Path, Path, Path]:
    root = get_video_session_root(session_id)
    return root / "video_configs", root / "video_components", root / "public" / "audio"

def _build_component_registry(task_id: str, session_id: str) -> dict[str, str]:
    config_dir, components_dir, _ = _video_dirs(session_id)
    config_path = config_dir / f"generated_{task_id}_aligned.json"
    if not config_path.exists():
        raise HTTPException(status_code=404, detail=f"Config not found for task_id: {task_id}")
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    comp_dir = components_dir / task_id
    if not comp_dir.exists():
        raise HTTPException(status_code=404, detail=f"Components dir not found for task_id: {task_id}")
    existing = {f.name for f in comp_dir.iterdir() if f.suffix == ".tsx"}
    registry: dict[str, str] = {}
    for sid, fname in expected_scene_component_files(config, task_id).items():
        if fname in existing:
            registry[sid] = fname
    return registry


class VideoFullResponse(BaseModel):
    task_id: str
    session_id: str
    config: dict
    registry: dict[str, str]
    files: dict[str, str]


@router.get("/preview-auth", status_code=204, response_class=Response)
async def authorize_preview_access(
    user_id: CurrentUserId,
    db: Session = Depends(get_db),
    session_id: str = Query(...),
    x_preview_container: str | None = Header(default=None, alias="X-Preview-Container"),
):
    """
    Nginx auth_request endpoint for /video-previews/*.
    Requires authenticated user and owned session_id.
    """
    normalized_session_id = _require_owned_session_id(session_id, user_id, db)
    if not x_preview_container:
        raise HTTPException(status_code=400, detail="Missing preview container header")

    match = _CONTAINER_PATTERN.fullmatch(x_preview_container.strip())
    if not match:
        raise HTTPException(status_code=400, detail="Invalid preview container")

    task_id = _validate_task_id_or_400(match.group(1))
    config_path = get_video_session_root(normalized_session_id) / "video_configs" / f"generated_{task_id}_aligned.json"
    if not config_path.exists():
        # Session exists but task/container does not belong to this session.
        raise HTTPException(status_code=403, detail="Preview access denied")
    return Response(status_code=204)


@router.get("/preview-url/{task_id}")
async def get_preview_url(
    task_id: str,
    user_id: CurrentUserId,
    db: Session = Depends(get_db),
    session_id: str = Query(...),
):
    normalized_session_id = _require_owned_session_id(session_id, user_id, db)
    normalized_task_id = _validate_task_id_or_400(task_id)
    config_path = get_video_session_root(normalized_session_id) / "video_configs" / f"generated_{normalized_task_id}_aligned.json"
    if not config_path.exists():
        raise HTTPException(status_code=404, detail=f"Config not found for task_id: {normalized_task_id}")
    return {
        "task_id": normalized_task_id,
        "session_id": normalized_session_id,
        "url": f"/video-previews/deepeye-video-{normalized_task_id}/",
    }


@router.get("/audio-status/{task_id}")
async def get_audio_status(
    task_id: str,
    user_id: CurrentUserId,
    db: Session = Depends(get_db),
    session_id: str = Query(...),
):
    normalized_session_id = _require_owned_session_id(session_id, user_id, db)
    normalized_task_id = _validate_task_id_or_400(task_id)
    config_dir, _, audio_dir = _video_dirs(normalized_session_id)
    config_path = config_dir / f"generated_{normalized_task_id}_aligned.json"
    if not config_path.exists():
        raise HTTPException(status_code=404, detail=f"Config not found for task_id: {normalized_task_id}")
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    narrations_with_audio: list[dict] = []
    for scene in config.get("scenes") or []:
        scene_id = scene.get("id", "unknown")
        for idx, narr in enumerate(scene.get("narration") or []):
            af = narr.get("audio_file")
            if not af:
                continue
            base_name = Path(af).name
            audio_path = audio_dir / base_name
            narrations_with_audio.append(
                {
                    "scene_id": scene_id,
                    "narr_idx": idx,
                    "audio_file": af,
                    "base_name": base_name,
                    "found_on_disk": audio_path.exists() and audio_path.is_file(),
                    "paths_checked": [str(audio_dir)],
                }
            )

    has_any_in_config = len(narrations_with_audio) > 0
    all_found = has_any_in_config and all(n["found_on_disk"] for n in narrations_with_audio)
    summary = (
        "no_audio_in_config"
        if not has_any_in_config
        else "all_audio_found"
        if all_found
        else "audio_in_config_but_files_missing"
    )
    return {
        "task_id": normalized_task_id,
        "session_id": normalized_session_id,
        "config_path": str(config_path),
        "audio_dir_used_by_api": str(audio_dir),
        "summary": summary,
        "narrations_with_audio": narrations_with_audio,
    }


@router.get("/audio/{filename:path}")
async def get_audio_file(
    filename: str,
    user_id: CurrentUserId,
    db: Session = Depends(get_db),
    session_id: str = Query(...),
):
    normalized_session_id = _require_owned_session_id(session_id, user_id, db)
    _, _, audio_dir = _video_dirs(normalized_session_id)

    if ".." in filename or filename.startswith("/"):
        raise HTTPException(status_code=400, detail="Invalid filename")
    base_name = Path(filename).name
    if base_name != filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    audio_path = audio_dir / base_name
    if not (audio_path.exists() and audio_path.is_file()):
        logger.warning(
            "Audio file not found: filename=%s session_id=%s dir=%s",
            base_name,
            normalized_session_id,
            str(audio_dir),
        )
        raise HTTPException(status_code=404, detail=f"Audio file not found: {base_name}")

    return FileResponse(path=str(audio_path), media_type="audio/wav", filename=base_name)


@router.get("/full/{task_id}", response_model=VideoFullResponse)
async def get_video_full(
    task_id: str,
    user_id: CurrentUserId,
    db: Session = Depends(get_db),
    session_id: str = Query(...),
):
    normalized_session_id = _require_owned_session_id(session_id, user_id, db)
    normalized_task_id = _validate_task_id_or_400(task_id)
    config_dir, components_dir, _ = _video_dirs(normalized_session_id)
    config_path = config_dir / f"generated_{normalized_task_id}_aligned.json"
    if not config_path.exists():
        raise HTTPException(status_code=404, detail=f"Config not found for task_id: {normalized_task_id}")
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    registry = _build_component_registry(normalized_task_id, normalized_session_id)
    comp_dir = components_dir / normalized_task_id
    files: dict[str, str] = {}
    for filename in registry.values():
        path = comp_dir / filename
        if path.exists():
            files[filename] = path.read_text(encoding="utf-8")
    return VideoFullResponse(
        task_id=normalized_task_id,
        session_id=normalized_session_id,
        config=config,
        registry=registry,
        files=files,
    )


@router.get("/components/{task_id}/{filename:path}", response_class=PlainTextResponse)
async def get_video_component_file(
    task_id: str,
    filename: str,
    user_id: CurrentUserId,
    db: Session = Depends(get_db),
    session_id: str = Query(...),
):
    normalized_session_id = _require_owned_session_id(session_id, user_id, db)
    normalized_task_id = _validate_task_id_or_400(task_id)
    if ".." in filename or not filename.endswith(".tsx"):
        raise HTTPException(status_code=400, detail="Invalid filename")

    _, components_dir, _ = _video_dirs(normalized_session_id)
    base = components_dir / normalized_task_id
    if not base.exists():
        raise HTTPException(status_code=404, detail=f"Task not found: {normalized_task_id}")

    path = (base / filename).resolve()
    if not str(path).startswith(str(components_dir.resolve())):
        raise HTTPException(status_code=403, detail="Path not allowed")
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {filename}")
    try:
        return path.read_text(encoding="utf-8")
    except Exception as e:
        logger.error(f"Error reading component file: {e}")
        raise HTTPException(status_code=500, detail=str(e))

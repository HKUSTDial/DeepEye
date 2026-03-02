"""Video generation API endpoints."""

import json
import re
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.core.config import get_video_session_root, get_video_workspace_root, normalize_session_id
from app.services.video_deploy_service import video_deployer
from deepeye.utils.logger import logger

router = APIRouter(prefix="/video", tags=["video"])

# Task ID 格式 YYYYMMDD_HHMMSS，用于校验与按 task 启动预览
_TASK_ID_RE = re.compile(r"^\d{8}_\d{6}$")


def _find_session_for_task(task_id: str) -> Optional[str]:
    """在 workspace/sessions 下查找包含该 task_id 配置的 session_id。"""
    root = get_video_workspace_root()
    sessions_dir = root / "sessions"
    if not sessions_dir.exists():
        return None
    config_name = f"generated_{task_id}_aligned.json"
    for path in sessions_dir.iterdir():
        if path.is_dir():
            config_path = path / "video_configs" / config_name
            if config_path.exists():
                return path.name
    return None


def _resolve_session_id_or_400(session_id: Optional[str]) -> str | None:
    try:
        return normalize_session_id(session_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _video_dirs(session_id: str | None) -> tuple[Path, Path]:
    root = get_video_session_root(session_id)
    return root / "video_configs", root / "video_components"


def _dataset_name_from_config(config: dict) -> str:
    """从 config meta.title 提取 dataset_name（与前端/auto_compose 一致）"""
    title = (config.get("meta") or {}).get("title") or ""
    # Python re 不支持 \p{L}\p{N}，改用保留字母数字和 Unicode 字母（包括中文）
    import unicodedata

    s = "".join(c for c in title if c.isalnum() or unicodedata.category(c).startswith("L")) or ""
    return s[:20] if len(s) > 20 else s


def _scene_id_to_filename(scene_id: str, dataset_name: str, task_id: str) -> str:
    """根据 scene_id 生成动画组件文件名"""
    scene_id_camel = "".join(w.capitalize() for w in scene_id.split("_"))
    need_component = scene_id in ("scene_opening", "scene_closing") or (
        "stat" in scene_id.lower() or scene_id.endswith("_statistics")
    )
    if need_component:
        return f"{dataset_name}_{scene_id_camel}_{task_id}ComponentAnimated.tsx"
    return f"{dataset_name}_{scene_id_camel}_{task_id}Animated.tsx"


def _build_component_registry(task_id: str, session_id: str | None) -> dict[str, str]:
    """返回 scene_id -> 文件名 的映射（仅包含实际存在的文件）"""
    config_dir, components_dir = _video_dirs(session_id)
    config_path = config_dir / f"generated_{task_id}_aligned.json"
    if not config_path.exists():
        raise HTTPException(status_code=404, detail=f"Config not found for task_id: {task_id}")
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    dataset_name = _dataset_name_from_config(config)
    if not dataset_name:
        dataset_name = "DataAnalysis"
    comp_dir = components_dir / task_id
    if not comp_dir.exists():
        raise HTTPException(status_code=404, detail=f"Components dir not found for task_id: {task_id}")
    existing = {f.name for f in comp_dir.iterdir() if f.suffix == ".tsx"}
    registry = {}
    for scene in config.get("scenes") or []:
        sid = scene.get("id")
        if not sid:
            continue
        fname = _scene_id_to_filename(sid, dataset_name, task_id)
        if fname in existing:
            registry[sid] = fname
    return registry


class VideoConfigResponse(BaseModel):
    """Video configuration response."""

    config: dict
    config_path: str
    task_id: Optional[str] = None
    session_id: Optional[str] = None


@router.get("/config/{task_id}", response_model=VideoConfigResponse)
async def get_video_config(task_id: str, session_id: Optional[str] = Query(default=None)):
    """
    Get video configuration by task ID.

    Args:
        task_id: Task ID (format: YYYYMMDD_HHMMSS)

    Returns:
        Video configuration JSON
    """
    try:
        normalized_session_id = _resolve_session_id_or_400(session_id)
        config_dir, _ = _video_dirs(normalized_session_id)
        config_path = config_dir / f"generated_{task_id}_aligned.json"

        if not config_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Video config not found for task_id: {task_id}",
            )

        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)

        return VideoConfigResponse(
            config=config,
            config_path=str(config_path),
            task_id=task_id,
            session_id=normalized_session_id,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reading video config: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal error: {str(e)}",
        )


class VideoConfigSaveRequest(BaseModel):
    """Request body for saving video config (e.g. from workflow run output)."""

    task_id: str
    config: dict[str, Any]
    session_id: Optional[str] = None


@router.post("/config", response_model=VideoConfigResponse)
async def save_video_config(body: VideoConfigSaveRequest, session_id: Optional[str] = Query(default=None)):
    """
    Save video config to backend workspace (so GET /config/{task_id} can find it).
    Used when workflow runs in worker and config is in run output; frontend calls this to persist.
    """
    try:
        normalized_session_id = _resolve_session_id_or_400(body.session_id or session_id)
        config_dir, _ = _video_dirs(normalized_session_id)
        config_dir.mkdir(parents=True, exist_ok=True)
        config_path = config_dir / f"generated_{body.task_id}_aligned.json"
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(body.config, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved video config to {config_path}")
        return VideoConfigResponse(
            config=body.config,
            config_path=str(config_path),
            task_id=body.task_id,
            session_id=normalized_session_id,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving video config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/components/{task_id}/registry")
async def get_video_components_registry(task_id: str, session_id: Optional[str] = Query(default=None)):
    """
    返回指定 task_id 的组件注册表：scene_id -> 文件名。
    用于前端按 task 动态加载 TSX 组件。
    """
    try:
        normalized_session_id = _resolve_session_id_or_400(session_id)
        registry = _build_component_registry(task_id, normalized_session_id)
        return {"task_id": task_id, "session_id": normalized_session_id, "registry": registry}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error building component registry: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class VideoFullResponse(BaseModel):
    """一次返回某 task 的 config + registry + 所有 TSX 文件内容，供前端注册后按 id 预览"""

    task_id: str
    session_id: Optional[str] = None
    config: dict
    registry: dict[str, str]  # scene_id -> filename
    files: dict[str, str]  # filename -> tsx content


@router.get("/full/{task_id}", response_model=VideoFullResponse)
async def get_video_full(task_id: str, session_id: Optional[str] = Query(default=None)):
    """
    按 task_id 一次返回：config、registry、以及所有 TSX 文件源码。
    前端拉取后编译并注册到缓存，即可根据 id 预览视频。
    """
    try:
        normalized_session_id = _resolve_session_id_or_400(session_id)
        config_dir, components_dir = _video_dirs(normalized_session_id)
        config_path = config_dir / f"generated_{task_id}_aligned.json"
        if not config_path.exists():
            raise HTTPException(status_code=404, detail=f"Config not found for task_id: {task_id}")
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        registry = _build_component_registry(task_id, normalized_session_id)
        comp_dir = components_dir / task_id
        files: dict[str, str] = {}
        for filename in registry.values():
            path = comp_dir / filename
            if path.exists():
                files[filename] = path.read_text(encoding="utf-8")
        return VideoFullResponse(
            task_id=task_id,
            session_id=normalized_session_id,
            config=config,
            registry=registry,
            files=files,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error building full video payload: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class StartPreviewRequest(BaseModel):
    """按 task_id 启动已有视频的预览容器（可省略 session_id，由后端按 workspace 查找）。"""

    task_id: str
    session_id: Optional[str] = None


@router.post("/start-preview")
async def start_video_preview(body: StartPreviewRequest):
    """
    为指定 task_id 启动预览容器（例如之前生成过的 20260302_140132）。
    若未传 session_id，则在 workspace/sessions 下自动查找包含该 task 配置的 session。
    返回与测试预览一致的 { status, url, task_id }，前端可据此继续轮询 iframe 就绪。
    """
    task_id = (body.task_id or "").strip()
    if not _TASK_ID_RE.match(task_id):
        raise HTTPException(
            status_code=400,
            detail="task_id must be in format YYYYMMDD_HHMMSS (e.g. 20260302_140132)",
        )
    session_id: Optional[str] = body.session_id and body.session_id.strip() or None
    if not session_id:
        session_id = _find_session_for_task(task_id)
        if not session_id:
            raise HTTPException(
                status_code=404,
                detail=f"No session found with config for task_id: {task_id}. Ensure the video was generated in this workspace.",
            )
    try:
        result = await video_deployer.deploy(task_id=task_id, session_id=session_id)
        url = result.get("url") or f"/video-previews/deepeye-video-{task_id}/"
        return {
            "status": result.get("status", "running"),
            "task_id": task_id,
            "url": url,
        }
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception("Start video preview failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/config/by-path")
async def get_video_config_by_path(path: str, session_id: Optional[str] = Query(default=None)):
    """
    Get video configuration by file path.

    Args:
        path: Full path to configuration file

    Returns:
        Video configuration JSON
    """
    try:
        normalized_session_id = _resolve_session_id_or_400(session_id)
        config_dir, _ = _video_dirs(normalized_session_id)

        config_path = Path(path)
        allowed_base = config_dir.resolve()
        resolved = config_path.resolve()
        if not str(resolved).startswith(str(allowed_base)):
            raise HTTPException(
                status_code=403,
                detail="Path not allowed. Must be under session video_configs directory",
            )

        if not resolved.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Video config not found: {path}",
            )

        with open(resolved, "r", encoding="utf-8") as f:
            config = json.load(f)

        return VideoConfigResponse(
            config=config,
            config_path=str(resolved),
            task_id=None,
            session_id=normalized_session_id,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reading video config: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal error: {str(e)}",
        )

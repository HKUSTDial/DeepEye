"""Video generation API endpoints"""

import json
import re
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from typing import Optional, Any

from app.core.config import get_video_workspace_root
from deepeye.utils.logger import logger

router = APIRouter(prefix="/video", tags=["video"])

_workspace_root = get_video_workspace_root()
CONFIG_DIR = _workspace_root / "video_configs"
COMPONENTS_DIR = _workspace_root / "video_components"


def _dataset_name_from_config(config: dict) -> str:
    """从 config meta.title 提取 dataset_name（与前端/auto_compose 一致）"""
    title = (config.get("meta") or {}).get("title") or ""
    # Python re 不支持 \p{L}\p{N}，改用保留字母数字和 Unicode 字母（包括中文）
    import unicodedata
    s = "".join(c for c in title if c.isalnum() or unicodedata.category(c).startswith('L')) or ""
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


def _build_component_registry(task_id: str) -> dict[str, str]:
    """返回 scene_id -> 文件名 的映射（仅包含实际存在的文件）"""
    config_path = CONFIG_DIR / f"generated_{task_id}_aligned.json"
    if not config_path.exists():
        raise HTTPException(status_code=404, detail=f"Config not found for task_id: {task_id}")
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    dataset_name = _dataset_name_from_config(config)
    if not dataset_name:
        dataset_name = "DataAnalysis"
    comp_dir = COMPONENTS_DIR / task_id
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
    """Video configuration response"""
    config: dict
    config_path: str
    task_id: Optional[str] = None


@router.get("/config/{task_id}", response_model=VideoConfigResponse)
async def get_video_config(task_id: str):
    """
    Get video configuration by task ID.

    Args:
        task_id: Task ID (format: YYYYMMDD_HHMMSS)

    Returns:
        Video configuration JSON
    """
    try:
        config_path = CONFIG_DIR / f"generated_{task_id}_aligned.json"

        if not config_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Video config not found for task_id: {task_id}"
            )

        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        return VideoConfigResponse(
            config=config,
            config_path=str(config_path),
            task_id=task_id
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reading video config: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal error: {str(e)}"
        )


class VideoConfigSaveRequest(BaseModel):
    """Request body for saving video config (e.g. from workflow run output)."""
    task_id: str
    config: dict[str, Any]


@router.post("/config", response_model=VideoConfigResponse)
async def save_video_config(body: VideoConfigSaveRequest):
    """
    Save video config to backend workspace (so GET /config/{task_id} can find it).
    Used when workflow runs in worker and config is in run output; frontend calls this to persist.
    """
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        config_path = CONFIG_DIR / f"generated_{body.task_id}_aligned.json"
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(body.config, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved video config to {config_path}")
        return VideoConfigResponse(
            config=body.config,
            config_path=str(config_path),
            task_id=body.task_id,
        )
    except Exception as e:
        logger.error(f"Error saving video config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/components/{task_id}/registry")
async def get_video_components_registry(task_id: str):
    """
    返回指定 task_id 的组件注册表：scene_id -> 文件名。
    用于前端按 task 动态加载 TSX 组件。
    """
    try:
        registry = _build_component_registry(task_id)
        return {"task_id": task_id, "registry": registry}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error building component registry: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class VideoFullResponse(BaseModel):
    """一次返回某 task 的 config + registry + 所有 TSX 文件内容，供前端注册后按 id 预览"""
    task_id: str
    config: dict
    registry: dict[str, str]  # scene_id -> filename
    files: dict[str, str]  # filename -> tsx content


@router.get("/full/{task_id}", response_model=VideoFullResponse)
async def get_video_full(task_id: str):
    """
    按 task_id 一次返回：config、registry、以及所有 TSX 文件源码。
    前端拉取后编译并注册到缓存，即可根据 id 预览视频。
    """
    try:
        config_path = CONFIG_DIR / f"generated_{task_id}_aligned.json"
        if not config_path.exists():
            raise HTTPException(status_code=404, detail=f"Config not found for task_id: {task_id}")
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        registry = _build_component_registry(task_id)
        comp_dir = COMPONENTS_DIR / task_id
        files: dict[str, str] = {}
        for filename in registry.values():
            path = comp_dir / filename
            if path.exists():
                files[filename] = path.read_text(encoding="utf-8")
        return VideoFullResponse(task_id=task_id, config=config, registry=registry, files=files)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error building full video payload: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/config/by-path")
async def get_video_config_by_path(path: str):
    """
    Get video configuration by file path.

    Args:
        path: Full path to configuration file

    Returns:
        Video configuration JSON
    """
    try:
        config_path = Path(path)

        allowed_base = CONFIG_DIR.resolve()
        if not str(config_path.resolve()).startswith(str(allowed_base)):
            raise HTTPException(
                status_code=403,
                detail="Path not allowed. Must be under video_configs directory"
            )

        if not config_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Video config not found: {path}"
            )

        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        return VideoConfigResponse(
            config=config,
            config_path=str(config_path),
            task_id=None
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reading video config: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal error: {str(e)}"
        )

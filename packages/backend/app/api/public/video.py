"""Public video API endpoints (no authentication required)"""

import json
import re
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse
from pydantic import BaseModel

from app.core.config import get_video_workspace_root
from deepeye.utils.logger import logger

router = APIRouter(prefix="/video", tags=["public-video"])

_workspace_root = get_video_workspace_root()
CONFIG_DIR = _workspace_root / "video_configs"
COMPONENTS_DIR = _workspace_root / "video_components"
AUDIO_DIR = _workspace_root / "public" / "audio"


def _dataset_name_from_config(config: dict) -> str:
    """从 config meta.title 提取 dataset_name（与前端/auto_compose 一致）"""
    title = (config.get("meta") or {}).get("title") or ""
    # Python re 不支持 \p{L}\p{N}，改用 \w（字母数字下划线）或手动过滤
    # 保留字母、数字、中文字符（使用 Unicode 范围）
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


class VideoFullResponse(BaseModel):
    """一次返回某 task 的 config + registry + 所有 TSX 文件内容，供前端注册后按 id 预览"""
    task_id: str
    config: dict
    registry: dict[str, str]  # scene_id -> filename
    files: dict[str, str]  # filename -> tsx content


@router.get("/audio-status/{task_id}")
async def get_audio_status(task_id: str):
    """
    诊断某 task 的音频：配置里是否有 audio_file、磁盘上是否能找到对应文件。
    用于排查「没有声音」是未生成音频还是 API 读不到文件。
    """
    config_path = CONFIG_DIR / f"generated_{task_id}_aligned.json"
    if not config_path.exists():
        raise HTTPException(status_code=404, detail=f"Config not found for task_id: {task_id}")
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    narrations_with_audio: list[dict] = []
    for scene in config.get("scenes") or []:
        scene_id = scene.get("id", "unknown")
        for idx, narr in enumerate(scene.get("narration") or []):
            af = narr.get("audio_file")
            if af:
                base_name = Path(af).name
                found_in: list[str] = []
                for base in [AUDIO_DIR, Path("/tmp/video_config_audio"), Path("/workspace/public/audio")]:
                    p = base / base_name
                    if p.exists() and p.is_file():
                        found_in.append(str(p))
                narrations_with_audio.append({
                    "scene_id": scene_id,
                    "narr_idx": idx,
                    "audio_file": af,
                    "base_name": base_name,
                    "found_on_disk": len(found_in) > 0,
                    "paths_checked": [str(AUDIO_DIR), "/tmp/video_config_audio", "/workspace/public/audio"],
                })

    has_any_in_config = len(narrations_with_audio) > 0
    all_found = has_any_in_config and all(n["found_on_disk"] for n in narrations_with_audio)
    summary = (
        "no_audio_in_config" if not has_any_in_config else
        "all_audio_found" if all_found else
        "audio_in_config_but_files_missing"
    )
    return {
        "task_id": task_id,
        "config_path": str(config_path),
        "audio_dir_used_by_api": str(AUDIO_DIR),
        "summary": summary,
        "narrations_with_audio": narrations_with_audio,
        "message": (
            "配置中没有任何 narration.audio_file，可能未配置 Azure TTS 或生成时被跳过/失败。"
            if not has_any_in_config else
            "配置中有音频引用且 API 都能在磁盘找到，若仍无声音请检查前端请求与 CORS。"
            if all_found else
            "配置中有 audio_file 但 API 在磁盘上找不到对应文件，请确认 backend-api 与 backend-worker 共用同一 workspace 卷（如 workspace_data:/workspace）。"
        ),
    }


@router.get("/audio/{filename:path}")
async def get_audio_file(filename: str):
    """
    Get audio file by filename (public endpoint).
    Looks in: 1) workspace public/audio (where video_generator copies), 2) /tmp/video_config_audio, 3) /workspace/public/audio.
    """
    try:
        # 安全：只允许文件名，禁止路径穿越
        if ".." in filename or filename.startswith("/"):
            raise HTTPException(status_code=400, detail="Invalid filename")
        base_name = Path(filename).name
        if base_name != filename:
            raise HTTPException(status_code=400, detail="Invalid filename")

        search_bases = [AUDIO_DIR, Path("/tmp/video_config_audio"), Path("/workspace/public/audio")]
        for base in search_bases:
            audio_path = base / base_name
            if audio_path.exists() and audio_path.is_file():
                return FileResponse(
                    path=str(audio_path),
                    media_type="audio/wav",
                    filename=base_name,
                )

        logger.warning(
            "Audio file not found: filename=%s tried_dirs=%s",
            base_name,
            [str(b) for b in search_bases],
        )
        raise HTTPException(
            status_code=404,
            detail=f"Audio file not found: {base_name}. Ensure backend-api and backend-worker share the same workspace volume (e.g. workspace_data:/workspace) so public/audio is visible."
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reading audio file: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal error: {str(e)}"
        )


@router.get("/full/{task_id}", response_model=VideoFullResponse)
async def get_video_full(task_id: str):
    """
    按 task_id 一次返回：config、registry、以及所有 TSX 文件源码（公开接口，无需认证）。
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


@router.get("/components/{task_id}/{filename:path}", response_class=PlainTextResponse)
async def get_video_component_file(task_id: str, filename: str):
    """
    返回指定 task 下某个 TSX 组件的源码（供前端动态编译用）。
    仅允许访问 /workspace/video_components/{task_id}/ 下的 .tsx 文件。
    """
    if ".." in filename or not filename.endswith(".tsx"):
        raise HTTPException(status_code=400, detail="Invalid filename")
    base = COMPONENTS_DIR / task_id
    if not base.exists():
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")
    path = (base / filename).resolve()
    if not str(path).startswith(str(COMPONENTS_DIR.resolve())):
        raise HTTPException(status_code=403, detail="Path not allowed")
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {filename}")
    try:
        return path.read_text(encoding="utf-8")
    except Exception as e:
        logger.error(f"Error reading component file: {e}")
        raise HTTPException(status_code=500, detail=str(e))

"""Video generator node - generates complete data video from data rows."""

from __future__ import annotations

import json
import logging
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from app.core.config import settings, get_video_workspace_root
from app.node.base import BaseNode
from app.node.video_config.generator import create_generator
from app.services.workflow_file_service import get_progress_publisher_by_workflow_id
from deepeye.workflows.models import Node, Port
from deepeye.workflows.registry import NodeSpec
from deepeye.workflows.runtime import ExecutionContext

logger = logging.getLogger(__name__)


def _language_to_code(language: str) -> str:
    """Convert language name to code (e.g., 'English' -> 'en-US')."""
    language_lower = language.lower()
    if "chinese" in language_lower or "中文" in language:
        return "zh-CN"
    elif "english" in language_lower or "英文" in language:
        return "en-US"
    # Default to English
    return "en-US"


def _extract_task_id_from_config_path(config_path: Path) -> str:
    """从配置文件路径提取 task_id"""
    import re
    filename = config_path.name
    # 匹配 generated_20260109_141432_aligned.json 或类似格式
    match = re.search(r'generated_(\d{8}_\d{6})', filename)
    if match:
        return match.group(1)
    else:
        # 如果没有匹配到，使用当前时间戳
        return datetime.now().strftime('%Y%m%d_%H%M%S')


def _list_audio_dir(path: Path, label: str) -> None:
    """诊断：列出目录下文件，便于排查无声音"""
    try:
        if path.exists() and path.is_dir():
            names = sorted(p.name for p in path.iterdir() if p.is_file())
            logger.info("[Audio] %s: dir=%s files=%s", label, path, names[:20] if len(names) > 20 else names)
        else:
            logger.info("[Audio] %s: dir=%s (not exists or not dir)", label, path)
    except Exception as e:
        logger.info("[Audio] %s: list failed %s", label, e)


class VideoGeneratorHandler:
    """Handler for video generator node."""

    def __init__(self, db, user_id) -> None:
        self.db = db
        self.user_id = user_id
        # 创建生成器实例
        self.generator = create_generator()

    def _add_default_time_ranges(self, config: dict[str, Any]) -> dict[str, Any]:
        """
        为配置添加默认的时间范围（当音频生成失败时的回退方案）
        
        Args:
            config: 原始配置
            
        Returns:
            添加了默认 time_range 的配置
        """
        from copy import deepcopy
        import math
        
        config_with_times = deepcopy(config)
        current_time = 0.0
        default_narration_duration = 3.0  # 每个 narration 默认 3 秒
        min_scene_duration = 5.0  # 每个场景至少 5 秒
        
        for scene in config_with_times.get("scenes", []):
            scene_start_time = current_time
            scene_time = 0.0
            
            # 为每个 narration 添加默认时间
            for idx, narr in enumerate(scene.get("narration", [])):
                narr_start = scene_start_time + scene_time
                narr_duration = default_narration_duration
                narr_end = narr_start + narr_duration
                
                narr["time_start"] = round(narr_start, 3)
                narr["time_end"] = round(narr_end, 3)
                scene_time += narr_duration
            
            # 如果场景没有 narration 或时间太短，使用最小持续时间
            if scene_time < min_scene_duration:
                scene_time = min_scene_duration
            
            scene_end_time = scene_start_time + scene_time
            scene["time_range"] = [
                round(scene_start_time, 3),
                round(scene_end_time, 3)
            ]
            
            current_time = scene_end_time
        
        # 更新 meta 中的 video_duration
        if "meta" not in config_with_times:
            config_with_times["meta"] = {}
        config_with_times["meta"]["video_duration"] = round(current_time, 2)
        
        logger.info(f"Added default time ranges: total duration = {current_time:.2f}s")
        return config_with_times

    def _generate_audio_and_align(
        self, config: dict[str, Any], language: str, task_id: str | None = None
    ) -> dict[str, Any]:
        """Generate audio and align timeline."""
        try:
            # 诊断：便于从 worker 日志直接看出无声音原因
            has_key = bool(settings.AZURE_SPEECH_KEY)
            has_region = bool(settings.AZURE_SPEECH_REGION)
            logger.info(
                "[Audio] AZURE_SPEECH_KEY=%s AZURE_SPEECH_REGION=%s",
                "set" if has_key else "MISSING",
                "set" if has_region else "MISSING",
            )
            if not has_key or not has_region:
                logger.warning(
                    "Azure Speech API not configured, skipping audio generation → config will have NO narration.audio_file"
                )
                return self._add_default_time_ranges(config)

            # 导入音频引擎
            from app.node.video_config.audio_engine import TTSGenerator, TimeAligner

            # 使用固定输出目录（/tmp/video_config_audio）
            audio_output_dir = Path("/tmp/video_config_audio")
            audio_output_dir.mkdir(parents=True, exist_ok=True)
            logger.info("[Audio] output_dir=%s (exists=%s)", audio_output_dir, audio_output_dir.exists())

            # 转换语言代码
            language_code = _language_to_code(language)

            # 提取所有 narrations
            narrations = []
            for scene in config.get("scenes", []):
                scene_id = scene.get("id", "unknown")
                for idx, narr in enumerate(scene.get("narration", [])):
                    if "text" in narr:
                        segment_id = f"{scene_id}_narr{idx}"
                        narrations.append({
                            "id": segment_id,
                            "text": narr["text"],
                            "ssml": narr.get("ssml"),
                        })

            if not narrations:
                logger.warning(
                    "[Audio] No narrations in config (no scene.narration with text) → config will have NO audio_file"
                )
                return self._add_default_time_ranges(config)
            logger.info("[Audio] narrations count=%d, segment_ids=%s", len(narrations), [n["id"] for n in narrations])

            # 生成音频
            tts_generator = TTSGenerator(
                output_dir=str(audio_output_dir),
                api_key=settings.AZURE_SPEECH_KEY,
                region=settings.AZURE_SPEECH_REGION,
            )

            audio_segments = tts_generator.generate_batch(
                narrations=narrations,
                language=language_code,
                verbose=True,  # 改为 True 以便调试
                max_workers=2,
            )

            if not audio_segments:
                logger.warning(
                    "[Audio] TTS returned 0 segments (expected %d) → config will have NO audio_file. Check Azure/network.",
                    len(narrations),
                )
                _list_audio_dir(audio_output_dir, "after TTS (empty)")
                return self._add_default_time_ranges(config)
            logger.info("[Audio] TTS returned %d segments", len(audio_segments))
            _list_audio_dir(audio_output_dir, "after TTS")

            # 对齐时间戳
            time_aligner = TimeAligner()
            aligned_result = time_aligner.align_config(config, audio_segments)
            
            # 检查对齐后的配置是否完整（所有 narration 都应该有时间字段）
            # 如果某些 narration 没有时间字段，说明音频匹配失败，使用默认时间补充
            needs_fallback = False
            for scene in aligned_result.config.get("scenes", []):
                for narr in scene.get("narration", []):
                    if "time_start" not in narr or "time_end" not in narr:
                        needs_fallback = True
                        break
                if needs_fallback:
                    break
            
            if needs_fallback:
                logger.warning("Some narrations are missing time fields after alignment, applying fallback")
                # 使用默认时间补充缺失的字段
                return self._add_default_time_ranges(aligned_result.config)

            # 复制音频文件到 workspace/public/audio/ 并更新路径
            import shutil
            workspace_root = get_video_workspace_root()
            public_audio_dir = workspace_root / "public" / "audio"
            public_audio_dir.mkdir(parents=True, exist_ok=True)
            
            # 使用传入的 task_id，如果没有则生成一个
            if not task_id:
                task_id = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # 复制音频文件到 workspace/public/audio/ 并更新配置中的路径
            for scene in aligned_result.config.get("scenes", []):
                scene_id = scene.get("id", "unknown")
                for narr_idx, narr in enumerate(scene.get("narration", [])):
                    if "audio_file" not in narr:
                        continue
                    audio_file_path = narr["audio_file"]
                    # 候选源路径：1) 绝对路径 2) tmp 下按 name 3) 按 TTS 命名 {scene_id}_narr{idx}.wav
                    candidates = []
                    if Path(audio_file_path).is_absolute():
                        candidates.append(Path(audio_file_path))
                    candidates.append(audio_output_dir / Path(audio_file_path).name)
                    candidates.append(audio_output_dir / f"{scene_id}_narr{narr_idx}.wav")
                    src_path = None
                    for c in candidates:
                        if c.exists() and c.is_file():
                            src_path = c
                            break
                    if src_path is not None:
                        new_filename = f"{task_id}_{scene_id}_narr{narr_idx}.wav"
                        dst_path = public_audio_dir / new_filename
                        shutil.copy2(src_path, dst_path)
                        logger.info(f"Copied audio file: {src_path.name} -> {new_filename}")
                        narr["audio_file"] = new_filename
                    else:
                        logger.warning(
                            "[Audio] File not found for %s narr%d, tried: %s → removing audio_file",
                            scene_id,
                            narr_idx,
                            [str(c) for c in candidates],
                        )
                        narr.pop("audio_file", None)

            n_with_audio = sum(1 for s in aligned_result.config.get("scenes", []) for n in s.get("narration", []) if n.get("audio_file"))
            logger.info("[Audio] copy done: %d narrations have audio_file", n_with_audio)
            if n_with_audio == 0:
                _list_audio_dir(audio_output_dir, "after copy (no audio_file left)")
            # 返回对齐后的配置
            return aligned_result.config

        except ImportError as e:
            logger.warning(f"Audio engine not available: {e}, adding default time ranges")
            import traceback
            logger.debug(f"Import error traceback: {traceback.format_exc()}")
            return self._add_default_time_ranges(config)
        except Exception as e:
            logger.error(f"Failed to generate audio: {e}, adding default time ranges")
            import traceback
            logger.error(f"Audio generation error traceback: {traceback.format_exc()}")
            return self._add_default_time_ranges(config)

    def _render_video(
        self, config: dict[str, Any], config_path: Path, workers: int = 5
    ) -> dict[str, Any]:
        """
        Render video components from configuration.
        
        Args:
            config: Video configuration dict
            config_path: Path to saved config file
            workers: Number of workers for parallel processing
            
        Returns:
            dict with video_path and video_info
        """
        try:
            # 提取 task_id
            task_id = _extract_task_id_from_config_path(config_path)
            
            # 确定输出目录（Docker 用 /workspace，本地用 VIDEO_WORKSPACE_DIR 或 .video_workspace）
            workspace_root = get_video_workspace_root()
            output_base = workspace_root / "video_components"
            output_base.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"Starting video rendering pipeline (task_id: {task_id})")
            
            # 调用 pipeline_full_video 脚本
            # 注意：这个脚本可能需要 Remotion 环境，如果不可用会失败
            script_dir = Path(__file__).parent / "video_render"
            pipeline_script = script_dir / "pipeline_full_video.py"
            
            if not pipeline_script.exists():
                logger.warning(f"Video render script not found: {pipeline_script}, skipping video rendering")
                return {
                    "video_path": None,
                    "video_info": {
                        "status": "skipped",
                        "reason": "Render script not found",
                    }
                }
            
            # 调用 pipeline 脚本
            # 注意：渲染脚本使用相对路径输出到 infographic_generation_modularity/output/
            # 工作目录设置为 script_dir.parent (app/node/)，所以实际输出在：
            # app/node/infographic_generation_modularity/output/claude_tsx_animated/{task_id}/
            # 
            # 为了统一输出位置，我们设置环境变量或修改工作目录
            # 但当前脚本不支持自定义输出路径，所以先使用默认路径，然后检查实际输出
            cmd = [
                "python",
                str(pipeline_script),
                "--config", str(config_path),
                "--workers", str(workers),
                "--serial",  # 使用串行模式更稳定
            ]
            
            # 设置环境变量，让脚本知道输出应该在哪里
            # 但当前脚本可能不支持，所以先检查实际输出位置
            env = os.environ.copy()
            env["VIDEO_OUTPUT_BASE"] = str(output_base)
            
            logger.info(f"Executing video render pipeline: {' '.join(cmd)}")
            logger.info(f"Working directory: {script_dir.parent}")
            
            # 实时输出渲染过程的日志（让用户看到进度）
            print("\n" + "="*70)
            print("🎬 开始视频渲染流程...")
            print("="*70)
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # 合并 stderr 到 stdout
                text=True,
                bufsize=1,  # 行缓冲，实时输出
                universal_newlines=True,
                cwd=str(script_dir.parent),  # 工作目录：app/node/
                env=env,
            )
            
            # 实时打印输出
            stdout_lines = []
            for line in process.stdout:
                line = line.rstrip()
                if line:  # 只打印非空行
                    print(f"   {line}")  # 实时显示渲染进度
                    stdout_lines.append(line)
            
            # 等待进程完成
            returncode = process.wait()
            
            # 构建结果对象（兼容原有代码）
            class SubprocessResult:
                def __init__(self, returncode, stdout, stderr=""):
                    self.returncode = returncode
                    self.stdout = stdout
                    self.stderr = stderr
            
            result = SubprocessResult(returncode, '\n'.join(stdout_lines))
            
            print("="*70)
            if returncode == 0:
                print("✅ 视频渲染流程完成")
            else:
                print(f"❌ 视频渲染流程失败 (返回码: {returncode})")
            print("="*70 + "\n")
            
            # 如果失败，记录完整输出用于调试
            if result.returncode != 0 and result.stdout:
                logger.error(f"Pipeline failed. Full output (last 2000 chars):\n{result.stdout[-2000:]}")
            
            if result.returncode != 0:
                logger.error(f"Video render pipeline failed with return code {result.returncode}")
                logger.error(f"Full stderr: {result.stderr}")
                return {
                    "video_path": None,
                    "video_info": {
                        "status": "failed",
                        "error": result.stderr[:500] if result.stderr else "Unknown error",
                        "returncode": result.returncode,
                    }
                }
            
            # 确定实际输出路径（渲染脚本使用的默认路径）
            # 渲染脚本输出到：infographic_generation_modularity/output/claude_tsx_animated/{task_id}/
            actual_output_base = script_dir.parent / "infographic_generation_modularity" / "output" / "claude_tsx_animated"
            actual_output_dir = actual_output_base / task_id
            
            # 同时创建 workspace 目录（用于 API 访问和文件浏览器显示）
            video_output_dir = output_base / task_id
            video_output_dir.mkdir(parents=True, exist_ok=True)
            
            # 检查输出目录和文件
            if actual_output_dir.exists():
                files = list(actual_output_dir.glob("*.tsx"))
                if files:
                    logger.info(f"Video rendering completed: {len(files)} TSX components generated in {actual_output_dir}")
                    
                    # 将文件复制到 workspace 目录，以便文件浏览器可以显示
                    import shutil
                    copied_count = 0
                    try:
                        for src_file in files:
                            dst_file = video_output_dir / src_file.name
                            shutil.copy2(src_file, dst_file)
                            copied_count += 1
                        logger.info(f"Copied {copied_count} files to workspace: {video_output_dir}")
                        print(f"\n✅ 已复制 {copied_count} 个组件文件到 workspace: {video_output_dir}")
                    except Exception as e:
                        logger.warning(f"Failed to copy files to workspace: {e}")
                        print(f"\n⚠️  复制文件到 workspace 失败: {e}")
                    
                    return {
                        "video_path": str(video_output_dir),  # 返回 workspace 路径，而不是后端代码路径
                        "video_info": {
                            "status": "success",
                            "task_id": task_id,
                            "config_path": str(config_path),
                            "output_dir": str(actual_output_dir),
                            "workspace_dir": str(video_output_dir),
                            "component_count": len(files),
                            "copied_to_workspace": copied_count,
                        }
                    }
                else:
                    # 目录存在但没有文件，说明脚本执行失败但没有正确返回错误码
                    logger.warning(f"Output directory exists but no TSX files found: {actual_output_dir}")
                    logger.warning(f"This usually means the render script failed silently. Check stdout/stderr above.")
                    # 返回失败状态，包含 stdout/stderr 信息用于调试
                    error_msg = "No TSX files generated. Render script may have failed silently."
                    if result.stdout:
                        error_msg += f"\nStdout preview: {result.stdout[-500:]}"
                    if result.stderr:
                        error_msg += f"\nStderr: {result.stderr[:500]}"
                    
                    return {
                        "video_path": None,
                        "video_info": {
                            "status": "failed",
                            "task_id": task_id,
                            "error": error_msg,
                            "output_dir": str(actual_output_dir),
                        }
                    }
            else:
                # 目录不存在，说明脚本完全没有执行或执行失败
                logger.warning(f"Output directory does not exist: {actual_output_dir}")
                error_msg = "Output directory was not created. Render script may have failed early."
                if result.stderr:
                    error_msg += f"\nStderr: {result.stderr[:500]}"
                
                return {
                    "video_path": None,
                    "video_info": {
                        "status": "failed",
                        "task_id": task_id,
                        "error": error_msg,
                    }
                }
            
        except ImportError as e:
            logger.warning(f"Video render module not available: {e}, skipping video rendering")
            return {
                "video_path": None,
                "video_info": {
                    "status": "skipped",
                    "reason": f"Module not available: {e}",
                }
            }
        except Exception as e:
            logger.error(f"Failed to render video: {e}", exc_info=True)
            return {
                "video_path": None,
                "video_info": {
                    "status": "failed",
                    "error": str(e),
                }
            }

    def execute(self, node: Node, inputs: dict[str, Any], context: object) -> dict[str, Any]:
        """Execute complete video generation (config + audio + rendering)."""
        # 获取进度发布函数（如果可用）
        publish_progress = None
        if isinstance(context, ExecutionContext):
            publish_progress = get_progress_publisher_by_workflow_id(context.workflow_id)
        
        # 从 inputs 获取数据和查询
        rows = inputs.get("rows", [])
        if not rows:
            raise ValueError("rows input is required")

        # Query can come from inputs or params (for simpler workflows)
        query = inputs.get("query") or node.params.get("query")
        if not query:
            raise ValueError("query input or params.query is required")

        # 从 params 获取配置参数
        language = node.params.get("language", "English")
        workers = node.params.get("workers", 5)

        # Step 1: generate video configuration
        step1_msg = "📹 Step 1/4: Generating video configuration..."
        logger.info("Step 1/4: Generating video configuration")
        if publish_progress:
            publish_progress(step1_msg)
        config = self.generator.generate(
            query=query,
            data=rows,
            language=language,
            verbose=False,
            skip_animations=False
        )
        if publish_progress:
            scene_count = len(config.get("scenes", []))
            publish_progress(f"✅ Step 1/4 Done: Generated {scene_count} scene configurations")

        # Step 2: generate audio and align timeline (default)
        # First generate task_id so audio files use correct naming
        task_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        # 立即把 task_id 发给前端，便于预览面板一早打开并加载（无需等 run_end）
        if publish_progress:
            publish_progress(f"📋 Task ID: {task_id}")
        step2_msg = "🎵 Step 2/4: Generating audio and aligning timeline..."
        logger.info("Step 2/4: Generating audio and aligning timeline")
        if publish_progress:
            publish_progress(step2_msg)
        config = self._generate_audio_and_align(config, language, task_id=task_id)
        if publish_progress:
            total_duration = config.get("meta", {}).get("video_duration", 0)
            publish_progress(f"✅ Step 2/4 Done: Audio generated, video duration {total_duration:.2f} seconds")

        # Step 3: save configuration file
        step3_msg = "💾 Step 3/4: Saving configuration file..."
        logger.info("Step 3/4: Saving configuration")
        if publish_progress:
            publish_progress(step3_msg)
        workspace_root = get_video_workspace_root()
        config_dir = workspace_root / "video_configs"
        config_dir.mkdir(parents=True, exist_ok=True)
        config_filename = f"generated_{task_id}_aligned.json"
        config_path = config_dir / config_filename
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        logger.info(f"Configuration saved to: {config_path}")
        
        # Verify file was actually written
        if config_path.exists():
            file_size = config_path.stat().st_size
            logger.info(f"✅ Configuration file verified: {config_path} ({file_size} bytes)")
            print(f"\n✅ Config file saved: {config_path}")
            print(f"   File size: {file_size} bytes")
            if publish_progress:
                publish_progress(f"✅ Step 3/4 Done: Config file saved ({file_size} bytes)")
        else:
            logger.error(f"❌ Configuration file was not created: {config_path}")
            print(f"\n❌ WARNING: Config file may not have been created: {config_path}")
            if publish_progress:
                publish_progress("⚠️ Step 3/4 Warning: Config file may not have been created")

        # Step 4: run video rendering pipeline
        step4_msg = "🎬 Step 4/4: Rendering video components..."
        logger.info("Step 4/4: Rendering video components")
        if publish_progress:
            publish_progress(step4_msg)
        video_result = self._render_video(config, config_path, workers=workers)
        video_info = video_result.get("video_info", {})
        video_status = video_info.get("status", "unknown")
        
        # Print clear video generation status
        print("\n" + "="*70)
        print("📊 Video generation summary")
        print("="*70)
        print(f"✅ Config file saved: {config_path}")
        print(f"📋 Task ID: {task_id}")
        
        if video_status == "success":
            component_count = video_info.get("component_count", 0)
            video_path = video_result.get("video_path")
            print(f"✅ TSX components generated successfully: {component_count} files")
            if video_path:
                print(f"📁 Components directory: {video_path}")
            if publish_progress:
                publish_progress(f"✅ Step 4/4 Done: TSX components generated successfully ({component_count} files)")
        elif video_status == "skipped":
            reason = video_info.get("reason", "Unknown reason")
            print(f"⚠️  TSX component generation skipped: {reason}")
            print("   Hint: this is usually because the Remotion environment is unavailable or the render script was not found")
            if publish_progress:
                publish_progress(f"⚠️ Step 4/4 Skipped: {reason}")
        elif video_status == "failed":
            error = video_info.get("error", "Unknown error")
            print(f"❌ TSX component generation failed: {error[:200]}")
            print("   Hint: check backend logs for detailed error information")
            if publish_progress:
                publish_progress(f"❌ Step 4/4 Failed: {error[:200]}")
        else:
            print(f"⚠️  Video render status unknown: {video_status}")
            if publish_progress:
                publish_progress(f"⚠️ Step 4/4 Unknown status: {video_status}")
        print("="*70 + "\n")
        
        if publish_progress:
            publish_progress(f"\n🎉 Video generation completed! Task ID: {task_id}")

        # 返回结果（包含配置和视频信息）
        return {
            "video_path": video_result.get("video_path"),
            "video_info": video_info,
            "config": config,  # 也返回配置，以便需要时使用
            "config_path": str(config_path),
            "task_id": task_id,  # 显式返回 task_id，方便前端使用
        }


class VideoGeneratorNode(BaseNode):
    """Node for generating complete data video from data rows."""

    node_type = "video.generator"

    @classmethod
    def spec(cls) -> NodeSpec:
        return NodeSpec(
            type=cls.node_type,
            description="Generate complete data video from data rows and user query. Includes configuration generation, audio synthesis, timeline alignment, and video component rendering.",
            inputs={
                "rows": Port(
                    schema="list[dict]",
                    required=True,
                    description="Input data rows to generate video",
                ),
                "query": Port(
                    schema="string",
                    required=False,  # Can also be provided via params.query
                    description="User query or analytical goal (can also be set in params.query)",
                )
            },
            outputs={
                "video_path": Port(
                    schema="string",
                    description="Path to generated video components directory",
                ),
                "video_info": Port(
                    schema="dict",
                    description="Video generation information (status, task_id, etc.)",
                ),
                "config": Port(
                    schema="dict",
                    description="Generated video configuration JSON",
                ),
                "config_path": Port(
                    schema="string",
                    description="Path to saved configuration file",
                ),
            },
            params_schema={
                "query": {
                    "type": "string",
                    "required": False,
                    "description": "User query or analytical goal (alternative to inputs.query)",
                },
                "language": {
                    "type": "string",
                    "required": False,
                    "description": "Output language (default: English)",
                    "default": "English",
                },
                "workers": {
                    "type": "integer",
                    "required": False,
                    "description": "Number of workers for video rendering (default: 5)",
                    "default": 5,
                },
            },
        )

    @classmethod
    def build_handler(cls, db, user_id, sandbox=None) -> VideoGeneratorHandler | None:
        return VideoGeneratorHandler(db, user_id)

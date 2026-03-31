from __future__ import annotations

import io
import os
import shutil
import tarfile
import tempfile
import traceback
from pathlib import Path

from app.node.video.render.component_registry import (
    scan_components_for_prefix,
    update_video_composer_with_mapping,
)

DOCKER_CONTROL_MODE = os.getenv("DOCKER_CONTROL_MODE", "local")


def _project_root() -> Path:
    current_file = Path(__file__)
    return current_file.parent.parent.parent.parent.parent.parent.parent


def copy_components_to_frontend(
    component_prefix: str,
    config_data: dict,
    task_id: str,
    animated_components_dir: Path,
) -> bool:
    """
    Copy generated animated components into the frontend source tree.
    """
    try:
        frontend_video_dir = _project_root() / "packages" / "frontend" / "src" / "components" / "video"
        target_dir = frontend_video_dir / component_prefix / task_id

        if not animated_components_dir.exists():
            print(f"⚠️  动画组件目录不存在: {animated_components_dir}")
            return False

        target_dir.mkdir(parents=True, exist_ok=True)
        print(f"\n📂 复制组件到前端目录: {target_dir}")

        found_components = scan_components_for_prefix(
            component_prefix,
            str(animated_components_dir),
            config_data,
            task_id,
        )
        if not found_components:
            print("⚠️  未找到匹配的组件")
            return False

        copied_count = 0
        for _, (component_name, _) in found_components.items():
            source_file = animated_components_dir / f"{component_name}.tsx"
            if not source_file.exists():
                print(f"   ⚠️  文件不存在: {source_file}")
                continue
            target_file = target_dir / f"{component_name}.tsx"
            shutil.copy2(source_file, target_file)
            copied_count += 1
            print(f"   ✅ {component_name}.tsx")

        print(f"✅ 已复制 {copied_count} 个组件到前端代码目录")

        is_docker = Path("/app").exists() and Path("/.dockerenv").exists()
        if not is_docker:
            return True

        frontend_container_dir = Path("/app/src/components/video")
        if frontend_container_dir.exists():
            container_target_dir = frontend_container_dir / component_prefix / task_id
            container_target_dir.mkdir(parents=True, exist_ok=True)
            print(f"\n📂 复制组件到前端容器运行目录: {container_target_dir}")

            container_copied_count = 0
            for _, (component_name, _) in found_components.items():
                source_file = animated_components_dir / f"{component_name}.tsx"
                if not source_file.exists():
                    continue
                container_target_file = container_target_dir / f"{component_name}.tsx"
                shutil.copy2(source_file, container_target_file)
                container_copied_count += 1
                print(f"   ✅ {component_name}.tsx → 前端容器")

            print(f"✅ 已复制 {container_copied_count} 个组件到前端容器运行目录")
            return True

        if DOCKER_CONTROL_MODE == "remote":
            print("⚠️  Remote Docker control mode enabled, skip optional Docker API frontend sync")
            return True

        try:
            import docker
        except ImportError:
            print("⚠️  docker 库未安装，跳过容器内复制（需要: pip install docker）")
            return True

        try:
            docker_client = docker.from_env()
            containers = docker_client.containers.list(filters={"status": "running"})
            frontend_container = next(
                (container for container in containers if "frontend" in container.name.lower()),
                None,
            )
            if not frontend_container:
                print("⚠️  未找到运行中的前端容器，跳过容器内复制")
                return True

            print(f"\n📦 通过 Docker API 复制到前端容器: {frontend_container.name}")
            with tempfile.TemporaryDirectory() as tmp_dir:
                tmp_path = Path(tmp_dir)
                component_tmp_dir = tmp_path / component_prefix / task_id
                component_tmp_dir.mkdir(parents=True, exist_ok=True)

                for _, (component_name, _) in found_components.items():
                    source_file = animated_components_dir / f"{component_name}.tsx"
                    if source_file.exists():
                        shutil.copy2(source_file, component_tmp_dir / f"{component_name}.tsx")

                tar_stream = io.BytesIO()
                with tarfile.open(fileobj=tar_stream, mode="w") as tar:
                    tar.add(tmp_path / component_prefix, arcname=component_prefix)
                tar_stream.seek(0)
                frontend_container.put_archive("/app/src/components/video/", tar_stream.getvalue())
            print("✅ 已通过 Docker API 复制组件到前端容器")
        except Exception as exc:
            print(f"⚠️  通过 Docker API 复制失败: {exc}（这是可选的，不影响主要功能）")
            traceback.print_exc()

        return True
    except Exception as exc:
        print(f"⚠️  复制组件到前端失败: {exc}")
        traceback.print_exc()
        return False


def update_frontend_video_composer(
    component_prefix: str,
    config_data: dict,
    task_id: str,
) -> bool:
    """
    Update the frontend VideoComposer.tsx import/mapping file when needed.
    """
    success = False
    try:
        backend_frontend_path = (
            _project_root()
            / "packages"
            / "frontend"
            / "src"
            / "components"
            / "video"
            / "VideoComposer.tsx"
        )
        if backend_frontend_path.exists():
            print(f"📝 更新后端容器中的前端代码: {backend_frontend_path}")
            try:
                if update_video_composer_with_mapping(
                    component_prefix,
                    config_data,
                    backend_frontend_path,
                    task_id,
                    is_frontend=True,
                ):
                    print("✅ 已更新后端容器中的前端代码")
                    success = True
            except Exception as exc:
                print(f"⚠️  更新后端容器中的前端代码失败: {exc}")

        is_docker = Path("/app").exists() and Path("/.dockerenv").exists()
        if not is_docker:
            return success

        frontend_container_path = Path("/app/src/components/video/VideoComposer.tsx")
        if frontend_container_path.exists():
            print(f"📝 更新前端容器运行文件: {frontend_container_path}")
            try:
                if update_video_composer_with_mapping(
                    component_prefix,
                    config_data,
                    frontend_container_path,
                    task_id,
                    is_frontend=True,
                ):
                    print("✅ 已更新前端容器运行文件")
                    success = True
            except Exception as exc:
                print(f"⚠️  更新前端容器运行文件失败: {exc}")
            return success

        if DOCKER_CONTROL_MODE == "remote":
            print("⚠️  Remote Docker control mode enabled, skip optional Docker API frontend update")
            return success

        try:
            import docker
        except ImportError:
            print("⚠️  docker 库未安装，跳过 Docker API 更新（需要: pip install docker）")
            return success

        try:
            docker_client = docker.from_env()
            containers = docker_client.containers.list(filters={"status": "running"})
            frontend_container = next(
                (container for container in containers if "frontend" in container.name.lower()),
                None,
            )
            if not frontend_container:
                return success

            print(f"📦 通过 Docker API 更新前端容器: {frontend_container.name}")
            temp_file = tempfile.NamedTemporaryFile(
                mode="w",
                suffix=".tsx",
                delete=False,
                encoding="utf-8",
            )
            temp_path = Path(temp_file.name)
            temp_file.close()

            try:
                bits, _ = frontend_container.get_archive("/app/src/components/video/VideoComposer.tsx")
                file_obj = io.BytesIO(b"".join(bits))
                with tarfile.open(fileobj=file_obj) as tar:
                    tar.extractall(path=temp_path.parent)
                extracted_file = temp_path.parent / "VideoComposer.tsx"
                if extracted_file.exists() and update_video_composer_with_mapping(
                    component_prefix,
                    config_data,
                    extracted_file,
                    task_id,
                    is_frontend=True,
                ):
                    tar_stream = io.BytesIO()
                    with tarfile.open(fileobj=tar_stream, mode="w") as tar_out:
                        tar_out.add(extracted_file, arcname="VideoComposer.tsx")
                    tar_stream.seek(0)
                    frontend_container.put_archive("/app/src/components/video/", tar_stream.getvalue())
                    print("✅ 已通过 Docker API 更新前端容器")
                    success = True
            except Exception as exc:
                print(f"⚠️  通过 Docker API 更新失败: {exc}")
            finally:
                if temp_path.exists():
                    temp_path.unlink()
                extracted_file = temp_path.parent / "VideoComposer.tsx"
                if extracted_file.exists():
                    extracted_file.unlink()
        except Exception as exc:
            print(f"⚠️  通过 Docker API 更新失败: {exc}（这是可选的，不影响主要功能）")

        return success
    except Exception as exc:
        print(f"⚠️  更新前端 VideoComposer.tsx 失败: {exc}")
        traceback.print_exc()
        return False

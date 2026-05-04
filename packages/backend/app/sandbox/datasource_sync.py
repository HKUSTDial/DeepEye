from __future__ import annotations

import json
import shlex
from typing import Any

from deepeye.utils.logger import logger

from app.sandbox.docker_sandbox import DockerSandbox
from app.datasource.services.specs import workspace_data_path

DATASOURCE_SYNC_MANIFEST_PATH = "/workspace/.deepeye/datasource_sync_manifest.json"


def build_datasource_manifest_entry(get_filename, datasource) -> dict[str, Any]:
    filename = get_filename(datasource)
    return {
        "storage_path": getattr(datasource, "storage_path", None),
        "filename": filename,
        "dest_path": workspace_data_path(filename),
    }


async def is_datasource_sync_current(
    *,
    sandbox: DockerSandbox,
    manifest: dict[str, dict[str, Any]],
    manifest_key: str,
    manifest_entry: dict[str, Any],
) -> bool:
    if manifest.get(manifest_key) != manifest_entry:
        return False
    dest_path = manifest_entry.get("dest_path")
    if not isinstance(dest_path, str) or not dest_path:
        return False
    result = await sandbox.exec_command(f"test -f {shlex.quote(dest_path)} && echo 'EXISTS' || echo 'NOT_FOUND'")
    return result.exit_code == 0 and "EXISTS" in result.stdout


async def load_datasource_sync_manifest(sandbox: DockerSandbox) -> dict[str, dict[str, Any]]:
    result = await sandbox.exec_command(f"cat {shlex.quote(DATASOURCE_SYNC_MANIFEST_PATH)}")
    if result.exit_code != 0 or not result.stdout.strip():
        return {}
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        logger.warning("[SandboxManager] Failed to parse datasource sync manifest, ignoring it")
        return {}
    if not isinstance(payload, dict):
        return {}
    return {str(key): value for key, value in payload.items() if isinstance(value, dict)}


async def write_datasource_sync_manifest(
    sandbox: DockerSandbox,
    manifest: dict[str, dict[str, Any]],
) -> None:
    payload = json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True)
    if hasattr(sandbox, "write_text_file"):
        await sandbox.write_text_file(DATASOURCE_SYNC_MANIFEST_PATH, payload)
        return
    await sandbox.write_file(DATASOURCE_SYNC_MANIFEST_PATH, payload.encode("utf-8"))

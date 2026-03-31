from __future__ import annotations

import base64
from typing import Any

import httpx

from app.core.config import settings


class DockerControlError(RuntimeError):
    """Raised when the internal Docker control service returns an error."""

    def __init__(self, detail: str, status_code: int | None = None) -> None:
        super().__init__(detail)
        self.status_code = status_code


class DockerControlClient:
    def __init__(self) -> None:
        self._base_url = settings.DOCKER_CONTROL_URL.rstrip("/")
        self._timeout = settings.DOCKER_CONTROL_TIMEOUT_SECONDS

    @property
    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {}
        api_key = (settings.DOCKER_CONTROL_API_KEY or "").strip()
        if api_key:
            headers["X-Internal-Api-Key"] = api_key
        return headers

    def _raise_for_response(self, response: httpx.Response) -> None:
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            detail: str
            try:
                payload = response.json()
            except Exception:
                payload = {}
            if isinstance(payload, dict):
                detail = str(payload.get("detail") or payload.get("message") or response.text)
            else:
                detail = response.text
            raise DockerControlError(detail, response.status_code) from exc

    async def _async_request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        async with httpx.AsyncClient(
            base_url=self._base_url,
            timeout=self._timeout,
            headers=self._headers,
        ) as client:
            response = await client.request(method, path, json=json, params=params)
        self._raise_for_response(response)
        if response.content:
            return response.json()
        return {}

    def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        with httpx.Client(
            base_url=self._base_url,
            timeout=self._timeout,
            headers=self._headers,
        ) as client:
            response = client.request(method, path, json=json, params=params)
        self._raise_for_response(response)
        if response.content:
            return response.json()
        return {}

    async def ensure_sandbox(self, session_id: str) -> dict[str, Any]:
        return await self._async_request("POST", f"/internal/runtime-control/sandbox/sessions/{session_id}/ensure")

    async def get_sandbox(self, session_id: str) -> dict[str, Any] | None:
        try:
            return await self._async_request("GET", f"/internal/runtime-control/sandbox/sessions/{session_id}")
        except DockerControlError as exc:
            if exc.status_code == 404:
                return None
            raise

    async def exec_sandbox_command(self, session_id: str, command: str) -> dict[str, Any]:
        return await self._async_request(
            "POST",
            f"/internal/runtime-control/sandbox/sessions/{session_id}/exec",
            json={"command": command},
        )

    async def write_sandbox_file(self, session_id: str, path: str, data: bytes) -> None:
        await self._async_request(
            "POST",
            f"/internal/runtime-control/sandbox/sessions/{session_id}/write-file",
            json={
                "path": path,
                "content_base64": base64.b64encode(data).decode("ascii"),
            },
        )

    async def start_sandbox(self, session_id: str) -> dict[str, Any]:
        return await self._async_request("POST", f"/internal/runtime-control/sandbox/sessions/{session_id}/start")

    async def stop_sandbox(self, session_id: str) -> dict[str, Any]:
        return await self._async_request("POST", f"/internal/runtime-control/sandbox/sessions/{session_id}/stop")

    async def destroy_sandbox(self, session_id: str, *, delete_data: bool = False) -> dict[str, Any]:
        return await self._async_request(
            "DELETE",
            f"/internal/runtime-control/sandbox/sessions/{session_id}",
            params={"delete_data": str(delete_data).lower()},
        )

    async def sync_sandbox_from_docker(self, session_id: str) -> dict[str, Any]:
        return await self._async_request(
            "POST",
            f"/internal/runtime-control/sandbox/sessions/{session_id}/sync",
        )

    async def get_sandbox_status(self, session_id: str) -> dict[str, Any]:
        return await self._async_request(
            "GET",
            f"/internal/runtime-control/sandbox/sessions/{session_id}/status",
        )

    def get_sandbox_status_sync(self, session_id: str) -> dict[str, Any]:
        return self._request(
            "GET",
            f"/internal/runtime-control/sandbox/sessions/{session_id}/status",
        )

    async def get_sandbox_stats(self) -> dict[str, Any]:
        return await self._async_request("GET", "/internal/runtime-control/sandbox/stats")

    def get_sandbox_stats_sync(self) -> dict[str, Any]:
        return self._request("GET", "/internal/runtime-control/sandbox/stats")

    async def start_sandbox_cleanup(self) -> dict[str, Any]:
        return await self._async_request("POST", "/internal/runtime-control/sandbox/cleanup/start")

    def start_sandbox_cleanup_sync(self) -> dict[str, Any]:
        return self._request("POST", "/internal/runtime-control/sandbox/cleanup/start")

    async def stop_sandbox_cleanup(self) -> dict[str, Any]:
        return await self._async_request("POST", "/internal/runtime-control/sandbox/cleanup/stop")

    def stop_sandbox_cleanup_sync(self) -> dict[str, Any]:
        return self._request("POST", "/internal/runtime-control/sandbox/cleanup/stop")

    async def cleanup_all_sandboxes(self) -> dict[str, Any]:
        return await self._async_request("POST", "/internal/runtime-control/sandbox/cleanup/all")

    def cleanup_all_sandboxes_sync(self) -> dict[str, Any]:
        return self._request("POST", "/internal/runtime-control/sandbox/cleanup/all")

    async def cleanup_session_previews(self, session_id: str) -> dict[str, Any]:
        return await self._async_request(
            "POST",
            f"/internal/runtime-control/previews/cleanup/session/{session_id}",
        )

    async def cleanup_all_previews(self) -> dict[str, Any]:
        return await self._async_request("POST", "/internal/runtime-control/previews/cleanup/all")

    def container_state(self, session_id: str) -> dict[str, Any]:
        return self._request("GET", f"/internal/runtime-control/sandbox/sessions/{session_id}/container")

    def container_exec(
        self,
        session_id: str,
        *,
        cmd: list[str] | str,
        demux: bool = False,
        workdir: str | None = None,
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            f"/internal/runtime-control/sandbox/sessions/{session_id}/container/exec",
            json={
                "cmd": cmd,
                "demux": demux,
                "workdir": workdir,
            },
        )

    def container_put_archive(self, session_id: str, path: str, archive_bytes: bytes) -> None:
        self._request(
            "POST",
            f"/internal/runtime-control/sandbox/sessions/{session_id}/container/archive",
            json={
                "path": path,
                "archive_base64": base64.b64encode(archive_bytes).decode("ascii"),
            },
        )

    def container_logs(self, session_id: str) -> bytes:
        payload = self._request(
            "GET",
            f"/internal/runtime-control/sandbox/sessions/{session_id}/container/logs",
        )
        return base64.b64decode(payload.get("output_base64") or "")

    async def deploy_video_preview(self, *, task_id: str, session_id: str) -> dict[str, Any]:
        return await self._async_request(
            "POST",
            "/internal/runtime-control/previews/video/deploy",
            json={"task_id": task_id, "session_id": session_id},
        )

    async def deploy_dashboard_preview(
        self,
        *,
        task_id: str,
        source_archive_bytes: bytes,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        return await self._async_request(
            "POST",
            "/internal/runtime-control/previews/dashboard/deploy",
            json={
                "task_id": task_id,
                "source_archive_base64": base64.b64encode(source_archive_bytes).decode("ascii"),
                "session_id": session_id,
            },
        )


def get_docker_control_client() -> DockerControlClient:
    return DockerControlClient()

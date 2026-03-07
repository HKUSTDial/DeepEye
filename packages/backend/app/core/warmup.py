from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import httpx

from app.core.config import settings
from deepeye.utils.logger import logger


@dataclass(slots=True)
class WarmupCheckResult:
    name: str
    ok: bool
    detail: str


class WarmupCheck(Protocol):
    name: str

    def run(self) -> WarmupCheckResult: ...


class LLMConfigurationCheck:
    name = "llm_configuration"

    def run(self) -> WarmupCheckResult:
        missing: list[str] = []
        if not (settings.LLM_API_KEY or "").strip():
            missing.append("LLM_API_KEY")
        if not (settings.LLM_BASE_URL or "").strip():
            missing.append("LLM_BASE_URL")
        if not (settings.LLM_MODEL or "").strip():
            missing.append("LLM_MODEL")
        if settings.LLM_MAX_TOKENS <= 0:
            missing.append("LLM_MAX_TOKENS>0")
        if missing:
            return WarmupCheckResult(
                name=self.name,
                ok=False,
                detail=f"Missing or invalid settings: {', '.join(missing)}",
            )
        return WarmupCheckResult(
            name=self.name,
            ok=True,
            detail=(
                f"model={settings.LLM_MODEL}, base_url={settings.LLM_BASE_URL}, "
                f"max_tokens={settings.LLM_MAX_TOKENS}"
            ),
        )


class LLMConnectivityCheck:
    name = "llm_connectivity"

    def run(self) -> WarmupCheckResult:
        base_url = (settings.LLM_BASE_URL or "").rstrip("/")
        url = f"{base_url}/chat/completions"
        payload = {
            "model": settings.LLM_MODEL,
            "messages": [{"role": "user", "content": "Reply with OK."}],
            "temperature": 0,
            "max_tokens": settings.LLM_MAX_TOKENS,
        }
        headers = {
            "Authorization": f"Bearer {settings.LLM_API_KEY}",
            "Content-Type": "application/json",
        }

        try:
            with httpx.Client(timeout=settings.STARTUP_WARMUP_TIMEOUT_SECONDS) as client:
                response = client.post(url, headers=headers, json=payload)
        except Exception as exc:
            return WarmupCheckResult(
                name=self.name,
                ok=False,
                detail=f"LLM warmup request failed: {exc}",
            )

        if response.status_code >= 400:
            snippet = response.text.strip()
            if len(snippet) > 400:
                snippet = snippet[:400] + "..."
            return WarmupCheckResult(
                name=self.name,
                ok=False,
                detail=(
                    f"LLM warmup request returned HTTP {response.status_code}: {snippet or '<empty body>'}"
                ),
            )

        return WarmupCheckResult(
            name=self.name,
            ok=True,
            detail="chat completions warmup succeeded",
        )


def default_warmup_checks() -> list[WarmupCheck]:
    return [
        LLMConfigurationCheck(),
        LLMConnectivityCheck(),
    ]


def run_startup_warmup(*, component: str) -> list[WarmupCheckResult]:
    if not settings.STARTUP_WARMUP_ENABLED:
        logger.info("[Warmup] skipped for %s because STARTUP_WARMUP_ENABLED=false", component)
        return []

    results: list[WarmupCheckResult] = []
    failures: list[WarmupCheckResult] = []
    for check in default_warmup_checks():
        result = check.run()
        results.append(result)
        if result.ok:
            logger.info("[Warmup][%s] %s ok: %s", component, result.name, result.detail)
        else:
            logger.error("[Warmup][%s] %s failed: %s", component, result.name, result.detail)
            failures.append(result)

    if failures and settings.STARTUP_WARMUP_STRICT:
        summary = "; ".join(f"{result.name}: {result.detail}" for result in failures)
        raise RuntimeError(f"{component} startup warmup failed: {summary}")

    return results

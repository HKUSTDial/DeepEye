import os

os.environ.setdefault("ALLOW_INSECURE_DEFAULTS", "true")
os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_BASE_URL", "http://localhost:8000/v1")
os.environ.setdefault("LLM_MODEL", "test-model")

from app.core.config import settings
from app.core.warmup import LLMConfigurationCheck, LLMConnectivityCheck, run_startup_warmup


class _FakeResponse:
    def __init__(self, status_code: int, text: str = "", payload: dict | None = None) -> None:
        self.status_code = status_code
        self.text = text
        self._payload = payload or {}

    def json(self) -> dict:
        return self._payload


class _FakeClient:
    def __init__(self, *, response: _FakeResponse, capture: dict, timeout: float) -> None:
        self._response = response
        self._capture = capture
        self._capture["timeout"] = timeout

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def post(self, url: str, *, headers: dict, json: dict):
        self._capture["url"] = url
        self._capture["headers"] = headers
        self._capture["json"] = json
        return self._response


def test_llm_configuration_check_uses_current_settings() -> None:
    check = LLMConfigurationCheck()
    result = check.run()

    assert result.ok is True
    assert settings.LLM_MODEL in result.detail
    assert str(settings.LLM_MAX_TOKENS) in result.detail


def test_llm_connectivity_check_posts_with_configured_max_tokens(monkeypatch) -> None:
    capture: dict = {}

    def _client_factory(*, timeout: float):
        return _FakeClient(
            response=_FakeResponse(200, payload={"choices": [{"message": {"content": "OK"}}]}),
            capture=capture,
            timeout=timeout,
        )

    monkeypatch.setattr("app.core.warmup.httpx.Client", _client_factory)

    result = LLMConnectivityCheck().run()

    assert result.ok is True
    assert capture["url"] == f"{settings.LLM_BASE_URL.rstrip('/')}/chat/completions"
    assert capture["json"]["model"] == settings.LLM_MODEL
    assert capture["json"]["max_tokens"] == settings.LLM_MAX_TOKENS
    assert capture["json"]["messages"][0]["content"] == "Reply with OK."


def test_run_startup_warmup_raises_on_strict_failure(monkeypatch) -> None:
    capture: dict = {}

    def _client_factory(*, timeout: float):
        return _FakeClient(
            response=_FakeResponse(400, text="Invalid max_tokens value"),
            capture=capture,
            timeout=timeout,
        )

    monkeypatch.setattr("app.core.warmup.httpx.Client", _client_factory)
    monkeypatch.setattr(settings, "STARTUP_WARMUP_ENABLED", True)
    monkeypatch.setattr(settings, "STARTUP_WARMUP_STRICT", True)

    try:
        run_startup_warmup(component="api")
        raise AssertionError("expected startup warmup to raise")
    except RuntimeError as exc:
        message = str(exc)
        assert "api startup warmup failed" in message
        assert "Invalid max_tokens value" in message

import os

os.environ.setdefault("ALLOW_INSECURE_DEFAULTS", "true")
os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_BASE_URL", "http://localhost:8000")
os.environ.setdefault("LLM_MODEL", "test-model")

from app.api.v1.system import get_runtime_summary
from app.runtime.services.metrics import runtime_metrics


def test_runtime_metrics_snapshot_and_summary_endpoint() -> None:
    runtime_metrics.increment("unit.counter", tags={"scope": "test"})
    runtime_metrics.set_gauge("unit.gauge", 3, tags={"scope": "test"})
    runtime_metrics.record_duration("unit.duration", 0.25, tags={"scope": "test"})

    snapshot = runtime_metrics.snapshot()
    assert snapshot["counters"]["unit.counter[scope=test]"] >= 1
    assert snapshot["gauges"]["unit.gauge[scope=test]"] == 3
    assert snapshot["timings"]["unit.duration[scope=test]"]["avg_seconds"] == 0.25

    summary = __import__("asyncio").run(get_runtime_summary())
    assert summary.metrics["counters"]["unit.counter[scope=test]"] >= 1

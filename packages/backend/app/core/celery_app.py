from celery import Celery
from celery.signals import worker_init

from app.core.config import settings
from app.core.warmup import run_startup_warmup

# Debug: Print Redis URL on import
print(f"[Celery] Using broker: {settings.REDIS_URL}")

# Initialize Celery app with explicit broker_url
celery_app = Celery("deepeye_tasks")

celery_app.conf.update(
    broker_url=settings.REDIS_URL,
    result_backend=settings.REDIS_URL,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    imports=["app.tasks.agent_tasks", "app.tasks.workflow_tasks"],
)

# Export for compatibility
REDIS_URL = settings.REDIS_URL


@worker_init.connect
def _run_worker_warmup(**_: object) -> None:
    run_startup_warmup(component="worker")

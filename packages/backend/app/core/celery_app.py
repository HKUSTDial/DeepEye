from celery import Celery
from celery.signals import worker_init

from app.core.config import settings
from app.core.warmup import run_startup_warmup
from deepeye.utils.logger import logger


def create_celery_app() -> Celery:
    app = Celery("deepeye_tasks")
    app.conf.update(
        broker_url=settings.REDIS_URL,
        result_backend=settings.REDIS_URL,
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        imports=["app.tasks.agent_tasks", "app.tasks.workflow_tasks"],
    )
    return app


celery_app = create_celery_app()
REDIS_URL = settings.REDIS_URL


@worker_init.connect
def _run_worker_warmup(**_: object) -> None:
    logger.info("Celery worker booting.")
    if not settings.CELERY_STARTUP_WARMUP_ENABLED:
        logger.info("Skipping worker startup warmup.")
        return

    run_startup_warmup(component="worker")

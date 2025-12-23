from celery import Celery
from app.core.config import settings

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
    imports=["app.tasks.agent_tasks"],
)

# Export for compatibility
REDIS_URL = settings.REDIS_URL

from celery import Celery
from app.core.config import settings

# Initialize Celery app
celery_app = Celery(
    "deepeye_tasks",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

# Export REDIS_URL for other modules if needed (e.g. chat.py used to import it)
# But ideally they should use settings.REDIS_URL directly.
# Keeping it for compatibility if there are other imports I missed, 
# but chat.py was updated.
REDIS_URL = settings.REDIS_URL

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Auto-discover tasks in the tasks module
    imports=["app.tasks.agent_tasks"] 
)


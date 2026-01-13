from app.core.celery_app import celery_app

# This file can be used as the entrypoint for the worker if needed,
# or you can point celery directly to app.core.celery_app
if __name__ == "__main__":
    celery_app.start()

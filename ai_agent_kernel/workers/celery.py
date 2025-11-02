from celery import Celery
from config.settings import settings
from config.logger import logger
import os

# Initialize Celery
celery_app = Celery(
    "ai_agent_kernel",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=['workers.tasks']
)

# Celery configuration
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    result_expires=3600,  # 1 hour
)

# Auto-discover tasks
celery_app.autodiscover_tasks(['workers.tasks'])


@celery_app.task(bind=True)
def debug_task(self):
    """Debug task for testing Celery worker"""
    logger.info(f'Request: {self.request!r}')
    return {"status": "success", "message": "Debug task completed"}


if __name__ == "__main__":
    celery_app.start()
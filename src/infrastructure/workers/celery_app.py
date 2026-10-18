from celery import Celery

from src.infrastructure.config import settings

# Initialize celery app
celery_app = Celery(
    "waypoint",
    broker=settings.BROKER_URL,
    backend=settings.BROKER_BACKEND_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,  # only ack after the task completes (crash safety)
    task_reject_on_worker_lost=True,  # re-queue if the worker dies mid-task
)

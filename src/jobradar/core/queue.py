"""Celery application and named queues."""

from celery import Celery
from kombu import Queue

from jobradar.core.settings import get_settings

settings = get_settings()
celery_app = Celery("jobradar", broker=settings.redis_url)
celery_app.conf.update(
    accept_content=["json"],
    broker_connection_retry_on_startup=True,
    task_acks_late=True,
    task_default_queue="default",
    task_default_serializer="json",
    task_queues=(
        Queue("discovery"),
        Queue("llm"),
        Queue("apply"),
        Queue("email"),
        Queue("default"),
    ),
    task_reject_on_worker_lost=True,
    task_routes={
        "jobradar.tasks.discovery.*": {"queue": "discovery"},
        "jobradar.tasks.llm.*": {"queue": "llm"},
        "jobradar.tasks.apply.*": {"queue": "apply"},
        "jobradar.tasks.email.*": {"queue": "email"},
    },
)

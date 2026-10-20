"""Celery application used for durable background order work."""
from celery import Celery
from kombu import Exchange, Queue

from app.core.config import settings


celery_app = Celery(
    "sirius_food",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.tasks.orders", "app.tasks.maintenance"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Europe/Moscow",
    enable_utc=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    broker_transport_options={"visibility_timeout": 3600},
    task_default_queue="default",
    task_default_exchange="default",
    task_default_routing_key="default",
    task_queues=(
        Queue("default", Exchange("default"), routing_key="default"),
        Queue("dlq", Exchange("dlq"), routing_key="dlq"),
    ),
    beat_schedule={
        "update-order-statistics-every-minute": {
            "task": "maintenance.update_order_statistics",
            "schedule": 60.0,
        }
    },
)

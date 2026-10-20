"""Shared Celery task behavior, including explicit dead-letter publishing."""
from typing import Any, Dict

from celery import Task


class DeadLetterTask(Task):
    """Send a serializable failure envelope to the DLQ after final failure."""

    abstract = True

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        envelope: Dict[str, Any] = {
            "task_id": task_id,
            "task_name": self.name,
            "args": list(args),
            "kwargs": kwargs,
            "error": str(exc),
        }
        self.app.send_task(
            "orders.dead_letter",
            args=[envelope],
            queue="dlq",
            routing_key="dlq",
        )
        super().on_failure(exc, task_id, args, kwargs, einfo)

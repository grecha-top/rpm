"""Idempotent order side effects executed by Celery workers."""
import time
from typing import Callable

from redis import RedisError

from app.core.celery_app import celery_app
from app.core.config import settings
from app.core.redis import redis_client
from app.tasks.base import DeadLetterTask


def _run_once(effect: str, order_id: int, operation: Callable[[], str]) -> str:
    completed_key = f"order:{order_id}:{effect}:completed"
    lock_key = f"order:{order_id}:{effect}:lock"
    try:
        if redis_client.exists(completed_key):
            return f"{effect} already completed for order {order_id}"
        acquired = redis_client.set(lock_key, "1", nx=True, ex=60)
        if not acquired:
            return f"{effect} already in progress for order {order_id}"
        try:
            result = operation()
            redis_client.setex(
                completed_key,
                settings.ORDER_TASK_IDEMPOTENCY_TTL,
                "1",
            )
            return result
        finally:
            redis_client.delete(lock_key)
    except RedisError:
        # Redis is required for the broker too. Raising makes Celery retry instead
        # of silently losing idempotency guarantees.
        raise


@celery_app.task(base=DeadLetterTask, name="orders.generate_pdf")
def generate_order_pdf(order_id: int) -> str:
    return _run_once(
        "pdf",
        order_id,
        lambda: _delayed_result(2, f"PDF generated for order {order_id}"),
    )


@celery_app.task(
    base=DeadLetterTask,
    name="orders.send_email",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    max_retries=3,
)
def send_order_email(order_id: int, email: str) -> str:
    def send() -> str:
        if order_id % 5 == 0:
            raise RuntimeError("Email service unavailable")
        return _delayed_result(1, f"Email sent to {email} for order {order_id}")

    return _run_once("email", order_id, send)


@celery_app.task(
    base=DeadLetterTask,
    name="orders.send_sms",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    max_retries=3,
)
def send_order_sms(order_id: int, phone: str) -> str:
    return _run_once(
        "sms",
        order_id,
        lambda: _delayed_result(1, f"SMS sent to {phone} for order {order_id}"),
    )


@celery_app.task(name="orders.dead_letter")
def dead_letter(envelope: dict) -> dict:
    """Marker task intentionally left in the ``dlq`` queue for inspection."""
    return envelope


def _delayed_result(seconds: int, result: str) -> str:
    time.sleep(seconds)
    return result

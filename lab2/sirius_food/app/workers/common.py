"""Idempotency and bounded retry helpers shared by RabbitMQ consumers."""
import json
from typing import Callable

from sqlalchemy.exc import IntegrityError

from app.core.rabbitmq import publish_raw
from app.models import ProcessedEvent


MAX_RETRIES = 3


def process_idempotently(
    db,
    consumer_name: str,
    event_id: str,
    handler: Callable[[], None],
) -> bool:
    if db.query(ProcessedEvent).filter_by(
        consumer_name=consumer_name,
        event_id=event_id,
    ).first():
        return False

    try:
        db.add(ProcessedEvent(consumer_name=consumer_name, event_id=event_id))
        db.flush()
        handler()
        db.commit()
        return True
    except IntegrityError:
        db.rollback()
        return False
    except Exception:
        db.rollback()
        raise


async def consume_with_retry(message, routing_key: str, handler: Callable[[dict], None]):
    try:
        event = json.loads(message.body.decode("utf-8"))
        handler(event)
    except Exception:
        retries = int((message.headers or {}).get("x-retry-count", 0))
        if retries < MAX_RETRIES:
            await publish_raw(
                routing_key,
                message.body,
                headers={"x-retry-count": retries + 1},
            )
            await message.ack()
        else:
            await message.reject(requeue=False)
        return
    await message.ack()

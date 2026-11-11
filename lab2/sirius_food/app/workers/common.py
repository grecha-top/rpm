"""Idempotency and bounded retry helpers shared by RabbitMQ consumers."""
import json
from typing import Callable

from sqlalchemy.exc import IntegrityError

from app.core.correlation import (
    CORRELATION_HEADER,
    bind_correlation_id,
    reset_correlation_id,
)
from app.core.logging import get_logger
from app.core.observability import extract_trace_context, traced
from app.core.rabbitmq import publish_raw
from app.models import ProcessedEvent


MAX_RETRIES = 3
logger = get_logger(__name__)


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
    headers = dict(message.headers or {})
    correlation_id = headers.get(CORRELATION_HEADER, "unknown")
    if isinstance(correlation_id, bytes):
        correlation_id = correlation_id.decode("utf-8")
    token = bind_correlation_id(str(correlation_id))
    trace_context = extract_trace_context(headers)
    try:
        with traced(
            "rabbitmq.consume",
            context=trace_context,
            attributes={"messaging.destination": routing_key},
        ):
            event = json.loads(message.body.decode("utf-8"))
            handler(event)
            logger.info(
                "event_consumed",
                event_type=event.get("event_type"),
                event_id=event.get("event_id"),
                routing_key=routing_key,
            )
    except Exception as exc:
        retries = int(headers.get("x-retry-count", 0))
        logger.exception(
            "event_processing_failed",
            routing_key=routing_key,
            retry_count=retries,
            error=str(exc),
        )
        if retries < MAX_RETRIES:
            retry_headers = dict(headers)
            retry_headers["x-retry-count"] = retries + 1
            await publish_raw(
                routing_key,
                message.body,
                headers=retry_headers,
            )
            await message.ack()
        else:
            await message.reject(requeue=False)
        return
    finally:
        reset_correlation_id(token)
    await message.ack()

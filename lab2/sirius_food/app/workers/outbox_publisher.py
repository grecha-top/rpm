"""Transactional Outbox relay with publisher confirms."""
import asyncio
from datetime import datetime, timezone

from app.core.correlation import bind_correlation_id, reset_correlation_id
from app.core.logging import get_logger, setup_logging
from app.core.observability import extract_trace_context, setup_tracing, traced
from app.core.rabbitmq import publish_event
from app.database import SessionLocal
from app.models import OutboxEvent


BATCH_SIZE = 50
logger = get_logger(__name__)


async def publish_batch() -> int:
    db = SessionLocal()
    try:
        events = (
            db.query(OutboxEvent)
            .filter(OutboxEvent.published_at.is_(None))
            .order_by(OutboxEvent.created_at)
            .with_for_update(skip_locked=True)
            .limit(BATCH_SIZE)
            .all()
        )
        published = 0
        for event in events:
            correlation_id = event.payload.get("correlation_id", "unknown")
            token = bind_correlation_id(correlation_id)
            try:
                parent_context = extract_trace_context(event.payload.get("trace_context"))
                with traced(
                    "outbox.publish",
                    context=parent_context,
                    attributes={
                        "messaging.destination": event.routing_key,
                        "messaging.message.id": event.id,
                    },
                ):
                    await publish_event(event.routing_key, event.payload)
                event.published_at = datetime.now(timezone.utc)
                event.last_error = None
                published += 1
                logger.info(
                    "outbox_event_published",
                    event_id=event.id,
                    event_type=event.event_type,
                    routing_key=event.routing_key,
                )
            except Exception as exc:
                event.attempts += 1
                event.last_error = str(exc)[:1000]
                logger.exception(
                    "outbox_event_publish_failed",
                    event_id=event.id,
                    event_type=event.event_type,
                    error=str(exc),
                )
            finally:
                reset_correlation_id(token)
            db.add(event)
        db.commit()
        return published
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


async def main():
    setup_logging()
    setup_tracing(service_name="sirius-outbox")
    while True:
        try:
            await publish_batch()
        except Exception as exc:
            logger.exception("outbox_publish_cycle_failed", error=str(exc))
        await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())

"""Transactional Outbox relay with publisher confirms."""
import asyncio
from datetime import datetime, timezone

from app.core.rabbitmq import publish_event
from app.database import SessionLocal
from app.models import OutboxEvent


BATCH_SIZE = 50


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
            try:
                await publish_event(event.routing_key, event.payload)
                event.published_at = datetime.now(timezone.utc)
                event.last_error = None
                published += 1
            except Exception as exc:
                event.attempts += 1
                event.last_error = str(exc)[:1000]
            db.add(event)
        db.commit()
        return published
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


async def main():
    while True:
        try:
            await publish_batch()
        except Exception as exc:
            print(f"[Outbox] publish cycle failed: {exc}")
        await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())

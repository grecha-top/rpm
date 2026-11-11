"""Consumer creating a kitchen order for every paid order event."""
import asyncio

from app.core.rabbitmq import declare_consumer_topology, get_connection
from app.core.logging import get_logger, setup_logging
from app.core.observability import setup_tracing
from app.database import SessionLocal
from app.models import KitchenOrder
from app.workers.common import consume_with_retry, process_idempotently


CONSUMER_NAME = "kitchen"
logger = get_logger(__name__)


def handle_order_paid(event: dict) -> bool:
    db = SessionLocal()
    try:
        payload = event["payload"]
        processed = process_idempotently(
            db,
            CONSUMER_NAME,
            event["event_id"],
            lambda: db.add(KitchenOrder(order_id=payload["order_id"], status="pending")),
        )
        logger.info(
            "order_received_by_kitchen",
            order_id=payload["order_id"],
            event_id=event["event_id"],
            duplicate=not processed,
        )
        return processed
    finally:
        db.close()


async def main():
    setup_logging()
    setup_tracing(service_name="sirius-kitchen")
    connection = await get_connection()
    channel = await connection.channel()
    await channel.set_qos(prefetch_count=10)
    queue = await declare_consumer_topology(
        channel,
        queue_name="kitchen_queue",
        routing_key="order.paid",
        dead_letter_routing_key="kitchen.failed",
    )

    async def process(message):
        await consume_with_retry(message, "order.paid", handle_order_paid)

    await queue.consume(process, no_ack=False)
    logger.info("kitchen_consumer_ready", queue="kitchen_queue")
    await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())

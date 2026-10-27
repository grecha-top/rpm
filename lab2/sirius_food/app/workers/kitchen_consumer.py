"""Consumer creating a kitchen order for every paid order event."""
import asyncio

from app.core.rabbitmq import declare_consumer_topology, get_connection
from app.database import SessionLocal
from app.models import KitchenOrder
from app.workers.common import consume_with_retry, process_idempotently


CONSUMER_NAME = "kitchen"


def handle_order_paid(event: dict) -> bool:
    db = SessionLocal()
    try:
        payload = event["payload"]
        return process_idempotently(
            db,
            CONSUMER_NAME,
            event["event_id"],
            lambda: db.add(KitchenOrder(order_id=payload["order_id"], status="pending")),
        )
    finally:
        db.close()


async def main():
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
    print("[Kitchen] waiting for order.paid events")
    await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())

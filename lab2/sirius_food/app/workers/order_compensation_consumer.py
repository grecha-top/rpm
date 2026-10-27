"""Saga participant compensating orders after delivery assignment failure."""
import asyncio

from app.core.rabbitmq import declare_consumer_topology, get_connection
from app.database import SessionLocal
from app.events.contracts import build_event
from app.models import Order, OutboxEvent, User
from app.workers.common import consume_with_retry, process_idempotently


CONSUMER_NAME = "order-compensation"


def handle_delivery_failed(event: dict) -> bool:
    db = SessionLocal()
    try:
        payload = event["payload"]

        def compensate():
            order = db.query(Order).filter(Order.id == payload["order_id"]).first()
            if not order or order.status == "cancelled":
                return
            if order.status != "paid":
                raise ValueError("Only a paid order can be compensated")
            user = db.query(User).filter(User.id == order.user_id).first()
            if not user:
                raise ValueError("Order customer not found")

            user.balance += order.total
            order.status = "cancelled"
            cancelled = build_event(
                "OrderCancelled",
                {
                    "order_id": order.id,
                    "customer_id": user.id,
                    "refunded_amount": order.total,
                    "reason": payload.get("reason", "Delivery failed"),
                },
                correlation_id=event["correlation_id"],
            )
            db.add_all(
                [
                    user,
                    order,
                    OutboxEvent(
                        id=cancelled["event_id"],
                        event_type=cancelled["event_type"],
                        routing_key="order.cancelled",
                        payload=cancelled,
                    ),
                ]
            )

        return process_idempotently(db, CONSUMER_NAME, event["event_id"], compensate)
    finally:
        db.close()


async def main():
    connection = await get_connection()
    channel = await connection.channel()
    await channel.set_qos(prefetch_count=10)
    queue = await declare_consumer_topology(
        channel,
        queue_name="order_compensation_queue",
        routing_key="delivery.failed",
        dead_letter_routing_key="order-compensation.failed",
    )

    async def process(message):
        await consume_with_retry(message, "delivery.failed", handle_delivery_failed)

    await queue.consume(process, no_ack=False)
    print("[Orders] waiting for delivery.failed events")
    await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())

"""Delivery-service consumer reacting independently to OrderPaid."""
import asyncio

from app.core.rabbitmq import declare_consumer_topology, get_connection
from app.database import SessionLocal
from app.events.contracts import build_event
from app.models import Delivery, OutboxEvent, Role, User
from app.workers.common import consume_with_retry, process_idempotently


CONSUMER_NAME = "delivery"


def _available_courier(db):
    couriers = (
        db.query(User)
        .join(Role, User.role_id == Role.id)
        .filter(Role.name == "courier", User.is_blocked.is_(False))
        .order_by(User.id)
        .all()
    )
    for courier in couriers:
        active = (
            db.query(Delivery)
            .filter(
                Delivery.courier_id == courier.id,
                Delivery.status.in_(("in_progress", "on_the_way")),
            )
            .first()
        )
        if not active:
            return courier
    return None


def handle_order_paid(event: dict) -> bool:
    db = SessionLocal()
    try:
        payload = event["payload"]

        def apply():
            existing = db.query(Delivery).filter_by(order_id=payload["order_id"]).first()
            if existing:
                return
            courier = _available_courier(db)
            if courier:
                db.add(
                    Delivery(
                        order_id=payload["order_id"],
                        courier_id=courier.id,
                        status="in_progress",
                    )
                )
                return

            failed = build_event(
                "DeliveryFailed",
                {
                    "order_id": payload["order_id"],
                    "customer_id": payload["customer_id"],
                    "amount": payload["amount"],
                    "reason": "No available courier",
                },
                correlation_id=event["correlation_id"],
            )
            db.add(
                OutboxEvent(
                    id=failed["event_id"],
                    event_type=failed["event_type"],
                    routing_key="delivery.failed",
                    payload=failed,
                )
            )

        return process_idempotently(db, CONSUMER_NAME, event["event_id"], apply)
    finally:
        db.close()


async def main():
    connection = await get_connection()
    channel = await connection.channel()
    await channel.set_qos(prefetch_count=10)
    queue = await declare_consumer_topology(
        channel,
        queue_name="delivery_queue",
        routing_key="order.paid",
        dead_letter_routing_key="delivery.failed-message",
    )

    async def process(message):
        await consume_with_retry(message, "order.paid", handle_order_paid)

    await queue.consume(process, no_ack=False)
    print("[Delivery] waiting for order.paid events")
    await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())

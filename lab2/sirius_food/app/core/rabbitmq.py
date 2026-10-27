"""RabbitMQ connection, topology and persistent publishing helpers."""
import json
from typing import Dict, Optional

import aio_pika
from aio_pika import DeliveryMode, ExchangeType, Message

from app.core.config import settings


EVENT_EXCHANGE = "sirius.events"
DEAD_LETTER_EXCHANGE = "sirius.dlx"


async def get_connection() -> aio_pika.RobustConnection:
    return await aio_pika.connect_robust(settings.RABBITMQ_URL)


async def declare_consumer_topology(
    channel: aio_pika.abc.AbstractChannel,
    queue_name: str,
    routing_key: str,
    dead_letter_routing_key: str,
):
    exchange = await channel.declare_exchange(
        EVENT_EXCHANGE,
        ExchangeType.TOPIC,
        durable=True,
    )
    dead_letter_exchange = await channel.declare_exchange(
        DEAD_LETTER_EXCHANGE,
        ExchangeType.DIRECT,
        durable=True,
    )
    dead_letter_queue = await channel.declare_queue(
        f"{queue_name}.dlq",
        durable=True,
    )
    await dead_letter_queue.bind(dead_letter_exchange, dead_letter_routing_key)

    queue = await channel.declare_queue(
        queue_name,
        durable=True,
        arguments={
            "x-dead-letter-exchange": DEAD_LETTER_EXCHANGE,
            "x-dead-letter-routing-key": dead_letter_routing_key,
        },
    )
    await queue.bind(exchange, routing_key)
    return queue


async def publish_event(routing_key: str, payload: dict) -> None:
    await publish_raw(routing_key, json.dumps(payload).encode("utf-8"))


async def publish_raw(
    routing_key: str,
    body: bytes,
    headers: Optional[Dict] = None,
) -> None:
    connection = await get_connection()
    async with connection:
        channel = await connection.channel(publisher_confirms=True)
        exchange = await channel.declare_exchange(
            EVENT_EXCHANGE,
            ExchangeType.TOPIC,
            durable=True,
        )
        await exchange.publish(
            Message(
                body=body,
                headers=headers or {},
                delivery_mode=DeliveryMode.PERSISTENT,
                content_type="application/json",
            ),
            routing_key=routing_key,
            mandatory=True,
        )

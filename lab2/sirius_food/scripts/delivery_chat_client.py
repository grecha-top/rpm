"""Small bidirectional-streaming demonstration client."""
from app.modules.delivery.grpc_client import DeliveryGrpcClient


def messages():
    yield {"delivery_id": 1, "sender_id": 1, "text": "Где заказ?"}
    yield {"delivery_id": 1, "sender_id": 1, "text": "Спасибо"}


if __name__ == "__main__":
    client = DeliveryGrpcClient()
    try:
        for response in client.chat_with_courier(messages()):
            print(response)
    finally:
        client.close()

"""Infrastructure adapter hiding gRPC from the FastAPI transport layer."""
from typing import Iterable, Iterator

import grpc

from app.core.config import settings
from app.generated import delivery_pb2, delivery_pb2_grpc


class DeliveryClientNotFoundError(Exception):
    pass


class DeliveryClientUnavailableError(Exception):
    pass


class DeliveryClientTimeoutError(Exception):
    pass


class DeliveryClientPermissionError(Exception):
    pass


class DeliveryClientConflictError(Exception):
    pass


class DeliveryGrpcClient:
    def __init__(self, target: str = None, timeout: float = 5.0):
        self.target = target or settings.DELIVERY_GRPC_URL
        self.timeout = timeout
        self.channel = grpc.insecure_channel(self.target)
        self.stub = delivery_pb2_grpc.DeliveryServiceStub(self.channel)

    def assign_courier(self, order_id: int, courier_id: int) -> dict:
        try:
            response = self.stub.AssignCourier(
                delivery_pb2.AssignCourierRequest(order_id=order_id, courier_id=courier_id),
                timeout=self.timeout,
            )
            return {"delivery_id": response.delivery_id, "status": response.status}
        except grpc.RpcError as exc:
            self._raise_domain_error(exc)

    def complete_delivery(self, delivery_id: int, actor_id: int, actor_is_admin: bool) -> dict:
        try:
            response = self.stub.CompleteDelivery(
                delivery_pb2.CompleteDeliveryRequest(
                    delivery_id=delivery_id,
                    actor_id=actor_id,
                    actor_is_admin=actor_is_admin,
                ),
                timeout=self.timeout,
            )
            return {"status": response.status}
        except grpc.RpcError as exc:
            self._raise_domain_error(exc)

    def get_delivery(self, order_id: int) -> dict:
        try:
            response = self.stub.GetDelivery(
                delivery_pb2.GetDeliveryRequest(order_id=order_id),
                timeout=self.timeout,
            )
            return self._as_dict(response)
        except grpc.RpcError as exc:
            self._raise_domain_error(exc)

    def list_deliveries(self, courier_id: int, include_all: bool = False) -> list:
        try:
            response = self.stub.ListCourierDeliveries(
                delivery_pb2.ListCourierDeliveriesRequest(
                    courier_id=courier_id,
                    include_all=include_all,
                ),
                timeout=self.timeout,
            )
            return [self._as_dict(item) for item in response.deliveries]
        except grpc.RpcError as exc:
            self._raise_domain_error(exc)

    def track_delivery(self, order_id: int) -> Iterator[dict]:
        try:
            stream = self.stub.TrackDelivery(
                delivery_pb2.TrackDeliveryRequest(order_id=order_id),
                timeout=30,
            )
            for item in stream:
                yield {
                    "delivery_id": item.delivery_id,
                    "status": item.status,
                    "occurred_at": item.occurred_at,
                }
        except grpc.RpcError as exc:
            self._raise_domain_error(exc)

    def chat_with_courier(self, messages: Iterable[dict]) -> Iterator[dict]:
        def request_iterator():
            for item in messages:
                yield delivery_pb2.ChatMessage(**item)

        try:
            for item in self.stub.ChatWithCourier(request_iterator(), timeout=30):
                yield {
                    "delivery_id": item.delivery_id,
                    "sender_id": item.sender_id,
                    "text": item.text,
                    "sent_at": item.sent_at,
                }
        except grpc.RpcError as exc:
            self._raise_domain_error(exc)

    @staticmethod
    def _as_dict(item) -> dict:
        return {
            "id": item.id,
            "order_id": item.order_id,
            "status": item.status,
            "courier_id": item.courier_id,
        }

    @staticmethod
    def _raise_domain_error(exc: grpc.RpcError):
        mapping = {
            grpc.StatusCode.NOT_FOUND: DeliveryClientNotFoundError,
            grpc.StatusCode.UNAVAILABLE: DeliveryClientUnavailableError,
            grpc.StatusCode.DEADLINE_EXCEEDED: DeliveryClientTimeoutError,
            grpc.StatusCode.PERMISSION_DENIED: DeliveryClientPermissionError,
            grpc.StatusCode.FAILED_PRECONDITION: DeliveryClientConflictError,
        }
        error_type = mapping.get(exc.code(), RuntimeError)
        raise error_type(exc.details() or exc.code().name) from exc

    def close(self):
        self.channel.close()

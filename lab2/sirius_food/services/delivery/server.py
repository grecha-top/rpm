"""gRPC transport for the delivery microservice."""
from concurrent import futures
from datetime import datetime, timezone
import time

import grpc

from app.core.config import settings
from app.database import SessionLocal
from app.generated import delivery_pb2, delivery_pb2_grpc
from services.delivery.repository import DeliveryRepository
from services.delivery.service import (
    CourierNotFoundError,
    DeliveryAccessDeniedError,
    DeliveryConflictError,
    DeliveryNotFoundError,
    DeliveryService,
    OrderNotFoundError,
)


def _record(delivery):
    return delivery_pb2.DeliveryRecord(
        id=delivery.id,
        order_id=delivery.order_id,
        status=delivery.status,
        courier_id=delivery.courier_id or 0,
    )


class DeliveryGrpcServicer(delivery_pb2_grpc.DeliveryServiceServicer):
    def _call(self, context, callback):
        db = SessionLocal()
        try:
            return callback(DeliveryService(DeliveryRepository(db)))
        except (OrderNotFoundError, CourierNotFoundError, DeliveryNotFoundError) as exc:
            context.abort(grpc.StatusCode.NOT_FOUND, exc.__class__.__name__)
        except DeliveryAccessDeniedError as exc:
            context.abort(grpc.StatusCode.PERMISSION_DENIED, str(exc))
        except DeliveryConflictError as exc:
            context.abort(grpc.StatusCode.FAILED_PRECONDITION, str(exc))
        finally:
            db.close()

    def AssignCourier(self, request, context):
        delivery = self._call(
            context,
            lambda service: service.assign_courier(request.order_id, request.courier_id),
        )
        return delivery_pb2.AssignCourierResponse(
            delivery_id=delivery.id,
            status=delivery.status,
        )

    def CompleteDelivery(self, request, context):
        delivery = self._call(
            context,
            lambda service: service.complete_delivery(
                request.delivery_id,
                request.actor_id,
                request.actor_is_admin,
            ),
        )
        return delivery_pb2.CompleteDeliveryResponse(status=delivery.status)

    def GetDelivery(self, request, context):
        delivery = self._call(
            context,
            lambda service: service.get_delivery(request.order_id),
        )
        return delivery_pb2.GetDeliveryResponse(
            id=delivery.id,
            order_id=delivery.order_id,
            status=delivery.status,
            courier_id=delivery.courier_id or 0,
        )

    def ListCourierDeliveries(self, request, context):
        deliveries = self._call(
            context,
            lambda service: service.list_deliveries(
                request.courier_id,
                request.include_all,
            ),
        )
        return delivery_pb2.ListCourierDeliveriesResponse(
            deliveries=[_record(delivery) for delivery in deliveries]
        )

    def TrackDelivery(self, request, context):
        delivery = self._call(
            context,
            lambda service: service.get_delivery(request.order_id),
        )
        statuses = [delivery.status]
        if delivery.status == "in_progress":
            statuses.extend(["on_the_way", "delivered"])
        elif delivery.status == "on_the_way":
            statuses.append("delivered")

        for index, status in enumerate(statuses):
            if not context.is_active():
                return
            if index:
                time.sleep(2)
                delivery = self._call(
                    context,
                    lambda service, new_status=status: service.repository.update_status(
                        service.get_delivery(request.order_id),
                        new_status,
                    ),
                )
            yield delivery_pb2.DeliveryStatus(
                delivery_id=delivery.id,
                status=status,
                occurred_at=datetime.now(timezone.utc).isoformat(),
            )

    def ChatWithCourier(self, request_iterator, context):
        for message in request_iterator:
            if not context.is_active():
                return
            yield delivery_pb2.ChatMessage(
                delivery_id=message.delivery_id,
                sender_id=0,
                text=f"Курьер получил: {message.text}",
                sent_at=datetime.now(timezone.utc).isoformat(),
            )


def create_server():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    delivery_pb2_grpc.add_DeliveryServiceServicer_to_server(
        DeliveryGrpcServicer(),
        server,
    )
    server.add_insecure_port("[::]:50051")
    return server


def serve():
    server = create_server()
    server.start()
    print(f"Delivery gRPC server started at {settings.DELIVERY_GRPC_URL}")
    server.wait_for_termination()


if __name__ == "__main__":
    serve()

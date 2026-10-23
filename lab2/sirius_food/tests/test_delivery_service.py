from types import SimpleNamespace

import pytest

from services.delivery.service import (
    DeliveryAccessDeniedError,
    DeliveryConflictError,
    DeliveryService,
)


class FakeDeliveryRepository:
    def __init__(self):
        self.order = SimpleNamespace(id=10, status="paid")
        self.courier = SimpleNamespace(
            id=20,
            role=SimpleNamespace(name="courier"),
            is_blocked=False,
        )
        self.delivery = None

    def get_order(self, order_id):
        return self.order if order_id == self.order.id else None

    def get_courier(self, courier_id):
        return self.courier if courier_id == self.courier.id else None

    def get_by_order(self, order_id):
        return self.delivery if self.delivery and self.delivery.order_id == order_id else None

    def get_by_id(self, delivery_id):
        return self.delivery if self.delivery and self.delivery.id == delivery_id else None

    def get_active_for_courier(self, courier_id):
        return None

    def create(self, order_id, courier_id):
        self.delivery = SimpleNamespace(
            id=1,
            order_id=order_id,
            courier_id=courier_id,
            status="in_progress",
        )
        return self.delivery

    def update_status(self, delivery, status):
        delivery.status = status
        return delivery


def test_assign_courier_creates_delivery_for_paid_order():
    repository = FakeDeliveryRepository()

    delivery = DeliveryService(repository).assign_courier(10, 20)

    assert delivery.id == 1
    assert delivery.status == "in_progress"


def test_assign_courier_rejects_duplicate_delivery():
    repository = FakeDeliveryRepository()
    service = DeliveryService(repository)
    service.assign_courier(10, 20)

    with pytest.raises(DeliveryConflictError, match="уже существует"):
        service.assign_courier(10, 20)


def test_courier_cannot_complete_another_couriers_delivery():
    repository = FakeDeliveryRepository()
    service = DeliveryService(repository)
    delivery = service.assign_courier(10, 20)

    with pytest.raises(DeliveryAccessDeniedError):
        service.complete_delivery(delivery.id, actor_id=99, actor_is_admin=False)

    completed = service.complete_delivery(delivery.id, actor_id=99, actor_is_admin=True)
    assert completed.status == "delivered"

from types import SimpleNamespace

import pytest

from app.modules.orders.service import (
    AccessDeniedError,
    OrderAlreadyPaidError,
    OrderService,
)


class FakeOrderRepository:
    def __init__(self):
        self.user = SimpleNamespace(
            id=1,
            email="student@example.com",
            phone="+79991234567",
            balance=1000.0,
        )
        self.item = SimpleNamespace(id=2, price=150.0, is_available=True)
        self.order = None
        self.next_id = 1

    def get_user_by_id(self, user_id):
        return self.user if user_id == self.user.id else None

    def get_menu_item_by_id(self, item_id):
        return self.item if item_id == self.item.id else None

    def save_order(self, user_id, item_id, quantity, total):
        self.order = SimpleNamespace(
            id=self.next_id,
            user_id=user_id,
            item_id=item_id,
            quantity=quantity,
            total=total,
            status="processing",
        )
        return self.order.id

    def get_order(self, order_id):
        return self.order if self.order and self.order.id == order_id else None

    def pay_order(self, order, user, new_balance):
        user.balance = new_balance
        order.status = "paid"


def test_create_order_persists_total_without_charging_user():
    repository = FakeOrderRepository()
    order_id = OrderService(repository).create_order(1, 2, 3)

    assert order_id == 1
    assert repository.order.total == 450.0
    assert repository.user.balance == 1000.0


def test_create_order_dispatches_background_effects():
    repository = FakeOrderRepository()
    dispatcher = SimpleNamespace(calls=[])
    dispatcher.dispatch_order_created = lambda *args: dispatcher.calls.append(args)

    OrderService(repository, dispatcher).create_order(1, 2, 1)

    assert dispatcher.calls == [(1, "student@example.com", "+79991234567")]


def test_pay_order_charges_balance_and_changes_status():
    repository = FakeOrderRepository()
    service = OrderService(repository)
    order_id = service.create_order(1, 2, 2)

    order = service.pay_order(order_id, repository.user)

    assert order.status == "paid"
    assert repository.user.balance == 700.0


def test_pay_order_rejects_foreign_and_repeated_payment():
    repository = FakeOrderRepository()
    service = OrderService(repository)
    order_id = service.create_order(1, 2, 1)

    with pytest.raises(AccessDeniedError):
        service.pay_order(order_id, SimpleNamespace(id=99, balance=1000.0))

    service.pay_order(order_id, repository.user)
    with pytest.raises(OrderAlreadyPaidError):
        service.pay_order(order_id, repository.user)

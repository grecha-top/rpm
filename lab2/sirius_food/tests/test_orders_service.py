from types import SimpleNamespace

import pytest

from app.modules.orders.service import (
    AccessDeniedError,
    OrderAlreadyPaidError,
    OrderNotFoundError,
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
        return self.user if self.user and user_id == self.user.id else None

    def get_menu_item_by_id(self, item_id):
        return self.item if self.item and item_id == self.item.id else None

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

    def pay_order(self, order, user, new_balance, event):
        user.balance = new_balance
        order.status = "paid"
        self.payment_event = event

    def save_order_entity(self, order):
        self.saved_order = order

    def get_all_orders(self):
        return [self.order] if self.order else []


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


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (lambda repository: setattr(repository, "user", None), "Пользователь не найден"),
        (lambda repository: setattr(repository, "item", None), "Блюдо не найдено"),
        (
            lambda repository: setattr(repository.item, "is_available", False),
            "Блюдо недоступно",
        ),
        (
            lambda repository: setattr(repository.user, "balance", 149.0),
            "Недостаточно средств на балансе студента",
        ),
    ],
)
def test_create_order_rejects_invalid_business_conditions(change, message):
    repository = FakeOrderRepository()
    change(repository)

    with pytest.raises(ValueError) as error:
        OrderService(repository).create_order(1, 2, 1)
    assert str(error.value) == message


def test_create_order_allows_exact_balance():
    repository = FakeOrderRepository()
    repository.user.balance = 150.0

    assert OrderService(repository).create_order(1, 2, 1) == 1


def test_dispatcher_receives_empty_phone_when_user_has_none():
    repository = FakeOrderRepository()
    repository.user.phone = None
    dispatcher = SimpleNamespace(calls=[])
    dispatcher.dispatch_order_created = lambda *args: dispatcher.calls.append(args)

    result = OrderService(repository, dispatcher).create_order(1, 2, 1)

    assert result == 1
    assert dispatcher.calls == [(1, "student@example.com", "")]


def test_pay_order_charges_balance_and_changes_status():
    repository = FakeOrderRepository()
    service = OrderService(repository)
    order_id = service.create_order(1, 2, 2)

    order = service.pay_order(
        order_id,
        repository.user,
        correlation_id="unit-pay-42",
        trace_context={"traceparent": "00-0123456789abcdef0123456789abcdef-0123456789abcdef-01"},
    )

    assert order.status == "paid"
    assert repository.user.balance == 700.0
    assert repository.payment_event["event_type"] == "OrderPaid"
    assert repository.payment_event["correlation_id"] == "unit-pay-42"
    assert repository.payment_event["trace_context"] == {
        "traceparent": "00-0123456789abcdef0123456789abcdef-0123456789abcdef-01"
    }
    assert repository.payment_event["payload"] == {
        "order_id": 1,
        "customer_id": 1,
        "amount": 300.0,
        "total": 300.0,
        "currency": "RUB",
    }


def test_pay_order_rejects_foreign_and_repeated_payment():
    repository = FakeOrderRepository()
    service = OrderService(repository)
    order_id = service.create_order(1, 2, 1)

    with pytest.raises(AccessDeniedError):
        service.pay_order(order_id, SimpleNamespace(id=99, balance=1000.0))

    service.pay_order(order_id, repository.user)
    with pytest.raises(OrderAlreadyPaidError):
        service.pay_order(order_id, repository.user)


def test_pay_order_rejects_missing_invalid_state_and_insufficient_balance():
    repository = FakeOrderRepository()
    service = OrderService(repository)

    with pytest.raises(OrderNotFoundError):
        service.pay_order(404, repository.user)

    order_id = service.create_order(1, 2, 1)
    repository.order.status = "cancelled"
    with pytest.raises(ValueError) as invalid_state:
        service.pay_order(order_id, repository.user)
    assert str(invalid_state.value) == "Заказ нельзя оплатить в текущем статусе"

    repository.order.status = "processing"
    repository.user.balance = 149.0
    with pytest.raises(ValueError) as insufficient_balance:
        service.pay_order(order_id, repository.user)
    assert str(insufficient_balance.value) == "Недостаточно средств на балансе студента"


def test_pay_order_allows_exact_balance():
    repository = FakeOrderRepository()
    order_id = OrderService(repository).create_order(1, 2, 1)
    repository.user.balance = repository.order.total

    OrderService(repository).pay_order(order_id, repository.user)

    assert repository.user.balance == 0
    assert repository.order.status == "paid"


def test_cancel_order_checks_state_and_persists_allowed_cancellation():
    repository = FakeOrderRepository()
    service = OrderService(repository)

    with pytest.raises(OrderNotFoundError):
        service.cancel_order(404, repository.user)

    order_id = service.create_order(1, 2, 1)
    for terminal_status in ("cancelled", "delivered"):
        repository.order.status = terminal_status
        with pytest.raises(ValueError) as terminal_error:
            service.cancel_order(order_id, repository.user)
        assert str(terminal_error.value) == "Заказ нельзя отменить в текущем статусе"

    repository.order.status = "processing"
    service.cancel_order(order_id, repository.user)
    assert repository.order.status == "cancelled"
    assert repository.saved_order is repository.order


def test_get_kitchen_orders_returns_repository_result():
    repository = FakeOrderRepository()
    service = OrderService(repository)
    service.create_order(1, 2, 1)

    assert service.get_kitchen_orders() == [repository.order]

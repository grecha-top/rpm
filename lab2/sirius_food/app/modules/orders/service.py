"""
Слой бизнес-логики модуля заказов.
"""
from typing import Protocol


class OrderNotFoundError(Exception):
    pass


class AccessDeniedError(Exception):
    pass


class OrderAlreadyPaidError(Exception):
    pass


class OrderRepositoryProtocol(Protocol):
    def get_user_by_id(self, user_id: int):
        ...

    def get_menu_item_by_id(self, item_id: int):
        ...

    def save_order(self, user_id: int, item_id: int, quantity: int, total: float) -> int:
        ...

    def get_order(self, order_id: int):
        ...

    def save_order_entity(self, order) -> None:
        ...

    def pay_order(self, order, user, new_balance: float) -> None:
        ...

    def get_all_orders(self):
        ...


class OrderTaskDispatcherProtocol(Protocol):
    def dispatch_order_created(self, order_id: int, email: str, phone: str) -> None:
        ...


class OrderService:
    """Инкапсулирует бизнес-правила оформления заказов."""

    def __init__(
        self,
        repository: OrderRepositoryProtocol,
        task_dispatcher: OrderTaskDispatcherProtocol = None,
    ):
        self.repository = repository
        self.task_dispatcher = task_dispatcher

    def create_order(self, user_id: int, item_id: int, quantity: int) -> int:
        user = self.repository.get_user_by_id(user_id)
        if not user:
            raise ValueError("Пользователь не найден")

        item = self.repository.get_menu_item_by_id(item_id)
        if not item:
            raise ValueError("Блюдо не найдено")

        if not item.is_available:
            raise ValueError("Блюдо недоступно")

        total_cost = item.price * quantity
        if user.balance < total_cost:
            raise ValueError("Недостаточно средств на балансе студента")

        order_id = self.repository.save_order(user_id, item_id, quantity, total_cost)
        if self.task_dispatcher:
            self.task_dispatcher.dispatch_order_created(
                order_id,
                user.email,
                user.phone or "",
            )
        return order_id

    def pay_order(self, order_id: int, current_user):
        order = self.repository.get_order(order_id)
        if not order:
            raise OrderNotFoundError()
        if order.user_id != current_user.id:
            raise AccessDeniedError()
        if order.status == "paid":
            raise OrderAlreadyPaidError()
        if order.status != "processing":
            raise ValueError("Заказ нельзя оплатить в текущем статусе")
        if current_user.balance < order.total:
            raise ValueError("Недостаточно средств на балансе студента")

        self.repository.pay_order(
            order,
            current_user,
            new_balance=current_user.balance - order.total,
        )
        return order

    def cancel_order(self, order_id: int, current_user) -> None:
        order = self.repository.get_order(order_id)
        if not order:
            raise OrderNotFoundError()
        if order.user_id != current_user.id:
            raise AccessDeniedError()
        if order.status in {"cancelled", "delivered"}:
            raise ValueError("Заказ нельзя отменить в текущем статусе")
        order.status = "cancelled"
        self.repository.save_order_entity(order)

    def get_kitchen_orders(self):
        return self.repository.get_all_orders()

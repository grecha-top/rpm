"""
Слой бизнес-логики модуля заказов.
"""
from typing import Protocol


class OrderRepositoryProtocol(Protocol):
    def get_user_by_id(self, user_id: int):
        ...

    def get_menu_item_by_id(self, item_id: int):
        ...

    def update_user_balance(self, user, new_balance: float) -> None:
        ...

    def save_order(self, user_id: int, item_id: int, quantity: int) -> int:
        ...


class OrderService:
    """Инкапсулирует бизнес-правила оформления заказов."""

    def __init__(self, repository: OrderRepositoryProtocol):
        self.repository = repository

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

        new_balance = user.balance - total_cost
        self.repository.update_user_balance(user, new_balance)
        return self.repository.save_order(user_id, item_id, quantity)

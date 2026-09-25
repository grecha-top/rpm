"""
Слой бизнес-логики модуля пользователей.
"""
from typing import Optional, Protocol


class UserRepositoryProtocol(Protocol):
    def get_by_id(self, user_id: int):
        ...

    def get_by_email(self, email: str):
        ...

    def create_user(self, email: str, phone: Optional[str]):
        ...

    def save_user(self, user) -> None:
        ...


class UserService:
    """Инкапсулирует бизнес-правила регистрации и пополнения баланса."""

    def __init__(self, repository: UserRepositoryProtocol):
        self.repository = repository

    def register_user(self, email: str, phone: Optional[str]):
        existing = self.repository.get_by_email(email)
        if existing:
            raise ValueError("Пользователь с таким email уже зарегистрирован")

        return self.repository.create_user(email=email, phone=phone)

    def top_up_balance(self, user_id: int, amount: float) -> float:
        user = self.repository.get_by_id(user_id)
        if not user:
            raise ValueError("Пользователь не найден")

        if user.is_blocked:
            raise PermissionError("Пользователь заблокирован. Пополнение невозможно")

        if amount > 50000:
            raise ValueError("Максимальная сумма пополнения — 50000 рублей")

        user.balance += amount
        self.repository.save_user(user)
        return user.balance

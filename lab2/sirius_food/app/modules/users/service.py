"""
Слой бизнес-логики модуля пользователей.
"""
from typing import Optional, Protocol

from app.core.security import hash_password


class UserRepositoryProtocol(Protocol):
    def get_by_id(self, user_id: int):
        ...

    def get_by_email(self, email: str):
        ...

    def create_user(self, email: str, phone: Optional[str]):
        ...

    def get_role_by_name(self, name: str):
        ...

    def save_user(self, user) -> None:
        ...


class UserService:
    """Инкапсулирует бизнес-правила регистрации и пополнения баланса."""

    def __init__(self, repository: UserRepositoryProtocol):
        self.repository = repository

    def register_user(self, email: str, password: str, phone: Optional[str]):
        existing = self.repository.get_by_email(email)
        if existing:
            raise ValueError("Пользователь с таким email уже зарегистрирован")

        if len(password) < 8:
            raise ValueError("Пароль должен содержать минимум 8 символов")

        role = self.repository.get_role_by_name("student")
        if not role:
            raise RuntimeError("Роль student не настроена")

        return self.repository.create_user(
            email=email,
            phone=phone,
            password_hash=hash_password(password),
            role_id=role.id,
        )

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

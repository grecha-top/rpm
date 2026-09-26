from types import SimpleNamespace
from typing import Optional

import pytest

from app.modules.users.service import UserService


class FakeUserRepository:
    def __init__(self):
        self.users_by_id = {}
        self.users_by_email = {}
        self.next_id = 1
        self.saved_user = None

    def get_by_id(self, user_id: int):
        return self.users_by_id.get(user_id)

    def get_by_email(self, email: str):
        return self.users_by_email.get(email)

    def create_user(self, email: str, phone: Optional[str]):
        user = SimpleNamespace(
            id=self.next_id,
            email=email,
            phone=phone,
            balance=0.0,
            is_blocked=False,
        )
        self.next_id += 1
        self.users_by_id[user.id] = user
        self.users_by_email[user.email] = user
        return user

    def save_user(self, user):
        self.saved_user = user


def test_register_user_creates_user_without_database():
    repository = FakeUserRepository()
    service = UserService(repository)

    user = service.register_user("student@example.com", "+79991234567")

    assert user.id == 1
    assert user.email == "student@example.com"
    assert user.balance == 0.0
    assert repository.get_by_email("student@example.com") is user


def test_top_up_balance_rejects_blocked_user_without_database():
    repository = FakeUserRepository()
    blocked_user = SimpleNamespace(
        id=1,
        email="blocked@example.com",
        phone=None,
        balance=100.0,
        is_blocked=True,
    )
    repository.users_by_id[1] = blocked_user
    service = UserService(repository)

    with pytest.raises(PermissionError, match="Пользователь заблокирован"):
        service.top_up_balance(user_id=1, amount=1000)

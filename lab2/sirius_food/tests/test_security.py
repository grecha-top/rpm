from types import SimpleNamespace

import pytest

from app.core.jwt import create_access_token, decode_token
from app.core.security import hash_password, verify_password
from app.modules.orders.service import AccessDeniedError, OrderService
from app.modules.auth.service import AuthService, InvalidCredentialsError


def test_password_is_hashed_and_verified():
    hashed = hash_password("secret-pass")
    assert hashed != "secret-pass"
    assert verify_password("secret-pass", hashed)
    assert not verify_password("wrong-pass", hashed)


def test_access_token_contains_user_and_type():
    payload = decode_token(create_access_token(42))
    assert payload["sub"] == "42"
    assert payload["type"] == "access"


class FakeAuthRepository:
    def __init__(self, user):
        self.user = user

    def get_by_email(self, email):
        return self.user if self.user.email == email else None

    def save_refresh_token(self, user_id, token, expires_at):
        self.saved = (user_id, token, expires_at)


def test_wrong_password_is_rejected():
    user = SimpleNamespace(
        id=1,
        email="student@example.com",
        password_hash=hash_password("correct-pass"),
        is_blocked=False,
    )
    with pytest.raises(InvalidCredentialsError):
        AuthService(FakeAuthRepository(user)).login(user.email, "wrong-pass")


class FakeOrderRepository:
    def __init__(self, order):
        self.order = order

    def get_order(self, order_id):
        return self.order if self.order.id == order_id else None


def test_foreign_order_is_rejected_as_idor():
    order = SimpleNamespace(id=10, user_id=2, status="processing")
    current_user = SimpleNamespace(id=1)
    with pytest.raises(AccessDeniedError):
        OrderService(FakeOrderRepository(order)).cancel_order(10, current_user)

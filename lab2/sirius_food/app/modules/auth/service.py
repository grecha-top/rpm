"""Authentication use cases without FastAPI dependencies."""
from datetime import datetime, timedelta
from typing import Protocol

from app.core.config import settings
from app.core.jwt import create_access_token, create_refresh_token, decode_token
from app.core.security import verify_password


class AuthRepositoryProtocol(Protocol):
    def get_by_email(self, email: str):
        ...

    def save_refresh_token(self, user_id: int, token: str, expires_at: datetime):
        ...

    def get_refresh_token(self, token: str):
        ...

    def revoke_refresh_token(self, record) -> None:
        ...

    def revoke_all_for_user(self, user_id: int) -> None:
        ...


class InvalidCredentialsError(Exception):
    pass


class InvalidRefreshTokenError(Exception):
    pass


class AuthService:
    def __init__(self, repository: AuthRepositoryProtocol):
        self.repository = repository

    def login(self, email: str, password: str) -> dict:
        user = self.repository.get_by_email(email)
        if not user or not user.password_hash or not verify_password(password, user.password_hash):
            raise InvalidCredentialsError()
        if user.is_blocked:
            raise InvalidCredentialsError()
        return self._issue_tokens(user.id)

    def refresh(self, refresh_token: str) -> dict:
        try:
            payload = decode_token(refresh_token)
            if payload.get("type") != "refresh":
                raise ValueError("wrong type")
            user_id = int(payload["sub"])
        except Exception as exc:
            raise InvalidRefreshTokenError() from exc

        record = self.repository.get_refresh_token(refresh_token)
        if not record or record.user_id != user_id:
            raise InvalidRefreshTokenError()
        if record.is_revoked or record.expires_at <= datetime.utcnow():
            self.repository.revoke_all_for_user(user_id)
            raise InvalidRefreshTokenError()

        self.repository.revoke_refresh_token(record)
        return self._issue_tokens(user_id)

    def _issue_tokens(self, user_id: int) -> dict:
        access_token = create_access_token(user_id)
        refresh_token = create_refresh_token(user_id)
        self.repository.save_refresh_token(
            user_id,
            refresh_token,
            datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_DAYS),
        )
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
        }

"""Persistence adapter for authentication data."""
from datetime import datetime
from hashlib import sha256

from sqlalchemy.orm import Session

from app.models import RefreshToken, User


def hash_token(token: str) -> str:
    return sha256(token.encode("utf-8")).hexdigest()


class AuthRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_email(self, email: str):
        return self.db.query(User).filter(User.email == email).first()

    def save_refresh_token(self, user_id: int, token: str, expires_at: datetime):
        record = RefreshToken(
            user_id=user_id,
            token_hash=hash_token(token),
            expires_at=expires_at,
            is_revoked=False,
        )
        self.db.add(record)
        self.db.commit()

    def get_refresh_token(self, token: str):
        return (
            self.db.query(RefreshToken)
            .filter(RefreshToken.token_hash == hash_token(token))
            .first()
        )

    def revoke_refresh_token(self, record: RefreshToken) -> None:
        record.is_revoked = True
        self.db.add(record)
        self.db.commit()

    def revoke_all_for_user(self, user_id: int) -> None:
        self.db.query(RefreshToken).filter(
            RefreshToken.user_id == user_id,
            RefreshToken.is_revoked.is_(False),
        ).update({"is_revoked": True}, synchronize_session=False)
        self.db.commit()

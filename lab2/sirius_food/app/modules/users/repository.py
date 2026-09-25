"""
Инфраструктурный слой модуля пользователей.
"""
from typing import Optional

from sqlalchemy.orm import Session

from app.models import User


class UserRepository:
    """Выполняет операции с пользователями через SQLAlchemy ORM."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, user_id: int):
        return self.db.query(User).filter(User.id == user_id).first()

    def get_by_email(self, email: str):
        return self.db.query(User).filter(User.email == email).first()

    def create_user(self, email: str, phone: Optional[str]) -> User:
        new_user = User(
            email=email,
            phone=phone,
            balance=0.0,
            is_blocked=False,
        )
        self.db.add(new_user)
        self.db.commit()
        self.db.refresh(new_user)
        return new_user

    def save_user(self, user) -> None:
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)

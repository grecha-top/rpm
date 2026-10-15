"""
Инфраструктурный слой модуля пользователей.
"""
from typing import Optional

from sqlalchemy.orm import Session

from app.models import Role, User


class UserRepository:
    """Выполняет операции с пользователями через SQLAlchemy ORM."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, user_id: int):
        return self.db.query(User).filter(User.id == user_id).first()

    def get_by_email(self, email: str):
        return self.db.query(User).filter(User.email == email).first()

    def get_role_by_name(self, name: str):
        return self.db.query(Role).filter(Role.name == name).first()

    def create_user(
        self,
        email: str,
        phone: Optional[str],
        password_hash: str,
        role_id: int,
    ) -> User:
        new_user = User(
            email=email,
            phone=phone,
            balance=0.0,
            is_blocked=False,
            password_hash=password_hash,
            role_id=role_id,
        )
        self.db.add(new_user)
        self.db.commit()
        self.db.refresh(new_user)
        return new_user

    def save_user(self, user) -> None:
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)

"""
Инфраструктурный слой модуля заказов.
"""
from sqlalchemy.orm import Session

from app.models import MenuItem, Order, User


class OrderRepository:
    """Выполняет операции ввода-вывода через SQLAlchemy ORM."""

    def __init__(self, db: Session):
        self.db = db

    def get_user_by_id(self, user_id: int):
        return self.db.query(User).filter(User.id == user_id).first()

    def get_menu_item_by_id(self, item_id: int):
        return self.db.query(MenuItem).filter(MenuItem.id == item_id).first()

    def save_order(self, user_id: int, item_id: int, quantity: int) -> int:
        new_order = Order(
            user_id=user_id,
            item_id=item_id,
            quantity=quantity,
            status="processing",
        )
        self.db.add(new_order)
        self.db.commit()
        self.db.refresh(new_order)
        return new_order.id

    def update_user_balance(self, user, new_balance: float) -> None:
        user.balance = new_balance
        self.db.add(user)
        self.db.commit()

    def get_order(self, order_id: int):
        return self.db.query(Order).filter(Order.id == order_id).first()

    def save_order_entity(self, order) -> None:
        self.db.add(order)
        self.db.commit()
        self.db.refresh(order)

    def get_all_orders(self):
        return self.db.query(Order).order_by(Order.id.desc()).all()

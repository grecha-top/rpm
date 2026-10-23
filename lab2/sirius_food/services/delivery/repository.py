"""Persistence adapter owned by the delivery service boundary."""
from app.models import Delivery, Order, User


class DeliveryRepository:
    def __init__(self, db):
        self.db = db

    def get_order(self, order_id: int):
        return self.db.query(Order).filter(Order.id == order_id).first()

    def get_courier(self, courier_id: int):
        return self.db.query(User).filter(User.id == courier_id).first()

    def get_by_id(self, delivery_id: int):
        return self.db.query(Delivery).filter(Delivery.id == delivery_id).first()

    def get_by_order(self, order_id: int):
        return self.db.query(Delivery).filter(Delivery.order_id == order_id).first()

    def get_active_for_courier(self, courier_id: int):
        return (
            self.db.query(Delivery)
            .filter(
                Delivery.courier_id == courier_id,
                Delivery.status.in_(("in_progress", "on_the_way")),
            )
            .first()
        )

    def list_for_courier(self, courier_id: int, include_all: bool):
        query = self.db.query(Delivery)
        if not include_all:
            query = query.filter(Delivery.courier_id == courier_id)
        return query.order_by(Delivery.id).all()

    def create(self, order_id: int, courier_id: int):
        delivery = Delivery(
            order_id=order_id,
            courier_id=courier_id,
            status="in_progress",
        )
        self.db.add(delivery)
        self.db.commit()
        self.db.refresh(delivery)
        return delivery

    def update_status(self, delivery, status: str):
        delivery.status = status
        if status == "delivered":
            order = self.get_order(delivery.order_id)
            if order:
                order.status = "delivered"
                self.db.add(order)
        self.db.add(delivery)
        self.db.commit()
        self.db.refresh(delivery)
        return delivery

"""
Модуль управления доставкой.
В MVP-версии содержит смешение слоёв и оставлен как исходный пример.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Delivery, Order, User
from app.schemas import DeliveryAssign

router = APIRouter()


@router.post("/assign")
def assign_courier(payload: DeliveryAssign, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == payload.order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")

    if order.status != "paid":
        raise HTTPException(
            status_code=400,
            detail="Курьера можно назначить только на оплаченный заказ",
        )

    courier = db.query(User).filter(User.id == payload.courier_id).first()
    if not courier:
        raise HTTPException(status_code=404, detail="Курьер не найден")

    if courier.is_blocked:
        raise HTTPException(
            status_code=403,
            detail="Курьер заблокирован и не может быть назначен",
        )

    active = db.query(Delivery).filter(
        Delivery.courier_id == payload.courier_id,
        Delivery.status == "in_progress",
    ).first()
    if active:
        raise HTTPException(
            status_code=400,
            detail="У курьера уже есть активная доставка",
        )

    new_delivery = Delivery(
        order_id=payload.order_id,
        courier_id=payload.courier_id,
        status="in_progress",
    )
    db.add(new_delivery)
    db.commit()
    db.refresh(new_delivery)

    return {"status": "success", "delivery_id": new_delivery.id}


@router.patch("/{delivery_id}/complete")
def complete_delivery(delivery_id: int, db: Session = Depends(get_db)):
    delivery = db.query(Delivery).filter(Delivery.id == delivery_id).first()
    if not delivery:
        raise HTTPException(status_code=404, detail="Доставка не найдена")

    if delivery.status == "completed":
        raise HTTPException(
            status_code=400,
            detail="Доставка уже завершена",
        )

    if delivery.status == "cancelled":
        raise HTTPException(
            status_code=400,
            detail="Отменённую доставку нельзя завершить",
        )

    delivery.status = "completed"

    order = db.query(Order).filter(Order.id == delivery.order_id).first()
    if order:
        order.status = "delivered"
        db.add(order)

    db.add(delivery)
    db.commit()

    return {"status": "success"}

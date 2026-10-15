"""Protected delivery endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, require_role
from app.database import get_db
from app.models import Delivery, Order, User
from app.schemas import DeliveryAssign


router = APIRouter()


@router.post("/assign")
def assign_courier(
    payload: DeliveryAssign,
    current_user: User = Depends(require_role("admin", "cook")),
    db: Session = Depends(get_db),
):
    order = db.query(Order).filter(Order.id == payload.order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")
    if order.status != "paid":
        raise HTTPException(status_code=400, detail="Курьера можно назначить только на оплаченный заказ")

    courier = db.query(User).filter(User.id == payload.courier_id).first()
    if not courier:
        raise HTTPException(status_code=404, detail="Курьер не найден")
    if not courier.role or courier.role.name != "courier":
        raise HTTPException(status_code=400, detail="Пользователь не является курьером")
    if courier.is_blocked:
        raise HTTPException(status_code=403, detail="Курьер заблокирован и не может быть назначен")

    active = db.query(Delivery).filter(
        Delivery.courier_id == payload.courier_id,
        Delivery.status == "in_progress",
    ).first()
    if active:
        raise HTTPException(status_code=400, detail="У курьера уже есть активная доставка")

    new_delivery = Delivery(
        order_id=payload.order_id,
        courier_id=payload.courier_id,
        status="in_progress",
    )
    db.add(new_delivery)
    db.commit()
    db.refresh(new_delivery)
    return {"status": "success", "delivery_id": new_delivery.id}


@router.get("/my")
def my_deliveries(
    current_user: User = Depends(require_role("courier", "admin")),
    db: Session = Depends(get_db),
):
    query = db.query(Delivery)
    if current_user.role.name != "admin":
        query = query.filter(Delivery.courier_id == current_user.id)
    return [
        {"id": item.id, "order_id": item.order_id, "courier_id": item.courier_id, "status": item.status}
        for item in query.order_by(Delivery.id).all()
    ]


@router.patch("/{delivery_id}/complete")
def complete_delivery(
    delivery_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    delivery = db.query(Delivery).filter(Delivery.id == delivery_id).first()
    if not delivery:
        raise HTTPException(status_code=404, detail="Доставка не найдена")
    if current_user.role.name != "admin" and delivery.courier_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    if delivery.status == "completed":
        raise HTTPException(status_code=400, detail="Доставка уже завершена")
    if delivery.status == "cancelled":
        raise HTTPException(status_code=400, detail="Отменённую доставку нельзя завершить")

    delivery.status = "completed"
    order = db.query(Order).filter(Order.id == delivery.order_id).first()
    if order:
        order.status = "delivered"
    db.add(delivery)
    db.commit()
    return {"status": "success"}

"""HTTP layer for authenticated order workflows."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, require_role
from app.database import get_db
from app.models import User
from app.modules.orders.repository import OrderRepository
from app.modules.orders.service import (
    AccessDeniedError,
    OrderAlreadyPaidError,
    OrderNotFoundError,
    OrderService,
)
from app.schemas import OrderCreate


router = APIRouter()


@router.post("/create")
def create_order(
    payload: OrderCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if payload.quantity <= 0:
        raise HTTPException(status_code=400, detail="Количество должно быть больше нуля")
    try:
        order_id = OrderService(OrderRepository(db)).create_order(
            user_id=current_user.id,
            item_id=payload.item_id,
            quantity=payload.quantity,
        )
    except ValueError as exc:
        status_code = 404 if str(exc) in {"Пользователь не найден", "Блюдо не найдено"} else 400
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc
    return {"status": "success", "order_id": order_id}


@router.post("/{order_id}/pay")
def pay_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        order = OrderService(OrderRepository(db)).pay_order(order_id, current_user)
    except OrderNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Заказ не найден") from exc
    except AccessDeniedError as exc:
        raise HTTPException(status_code=403, detail="Access denied") from exc
    except OrderAlreadyPaidError as exc:
        raise HTTPException(status_code=409, detail="Заказ уже оплачен") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"status": "success", "order_id": order.id, "order_status": order.status}


@router.post("/{order_id}/cancel")
def cancel_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        OrderService(OrderRepository(db)).cancel_order(order_id, current_user)
    except OrderNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Заказ не найден") from exc
    except AccessDeniedError as exc:
        raise HTTPException(status_code=403, detail="Access denied") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"status": "success"}


@router.get("/kitchen/orders")
def kitchen_orders(
    current_user: User = Depends(require_role("cook", "admin")),
    db: Session = Depends(get_db),
):
    orders = OrderService(OrderRepository(db)).get_kitchen_orders()
    return [
        {
            "id": order.id,
            "user_id": order.user_id,
            "item_id": order.item_id,
            "quantity": order.quantity,
            "status": order.status,
        }
        for order in orders
    ]

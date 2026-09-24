"""
Транспортный слой модуля заказов.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.modules.orders.repository import OrderRepository
from app.modules.orders.service import OrderService
from app.schemas import OrderCreate

router = APIRouter()


@router.post("/create")
def create_order(payload: OrderCreate, db: Session = Depends(get_db)):
    if payload.quantity <= 0:
        raise HTTPException(
            status_code=400,
            detail="Количество должно быть больше нуля",
        )

    repository = OrderRepository(db)
    service = OrderService(repository)

    try:
        order_id = service.create_order(
            user_id=payload.user_id,
            item_id=payload.item_id,
            quantity=payload.quantity,
        )
    except ValueError as exc:
        status_code = 404 if str(exc) in {"Пользователь не найден", "Блюдо не найдено"} else 400
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc

    return {"status": "success", "order_id": order_id}

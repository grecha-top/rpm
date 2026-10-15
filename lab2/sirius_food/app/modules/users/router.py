"""
Транспортный слой модуля пользователей.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.dependencies import get_current_user
from app.modules.users.repository import UserRepository
from app.modules.users.service import UserService
from app.schemas import UserCreate

router = APIRouter()


@router.post("/register")
def register_user(payload: UserCreate, db: Session = Depends(get_db)):
    if payload.phone and len(payload.phone) < 10:
        raise HTTPException(
            status_code=400,
            detail="Некорректный формат номера телефона",
        )

    service = UserService(UserRepository(db))

    try:
        new_user = service.register_user(
            email=payload.email,
            password=payload.password,
            phone=payload.phone,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "status": "success",
        "user_id": new_user.id,
        "email": new_user.email,
    }


@router.post("/{user_id}/topup")
def top_up_balance(
    user_id: int,
    amount: float,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    if amount <= 0:
        raise HTTPException(
            status_code=400,
            detail="Сумма пополнения должна быть положительной",
        )

    service = UserService(UserRepository(db))

    try:
        new_balance = service.top_up_balance(user_id=user_id, amount=amount)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        status_code = 404 if str(exc) == "Пользователь не найден" else 400
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc

    return {"status": "success", "new_balance": new_balance}

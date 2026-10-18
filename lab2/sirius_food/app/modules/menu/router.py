"""HTTP layer for public menu reads and protected menu mutations."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.dependencies import require_role
from app.database import get_db
from app.models import User
from app.modules.menu.repository import MenuRepository
from app.modules.menu.service import (
    MenuItemNameExistsError,
    MenuItemNotFoundError,
    MenuService,
)
from app.schemas import MenuItemCreate, MenuItemUpdate


router = APIRouter()


def _as_dict(item):
    return {
        "id": item.id,
        "name": item.name,
        "price": item.price,
        "is_available": item.is_available,
        "category_id": item.category_id,
    }


@router.get("/items")
def get_menu_items(db: Session = Depends(get_db)):
    items = MenuService(MenuRepository(db)).get_items()
    return [_as_dict(item) for item in items]


@router.get("/items/{item_id}")
def get_menu_item(item_id: int, db: Session = Depends(get_db)):
    try:
        item = MenuService(MenuRepository(db)).get_item(item_id)
    except MenuItemNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Блюдо не найдено") from exc
    return _as_dict(item)


@router.get("/categories/{category_id}")
def get_category_items(category_id: int, db: Session = Depends(get_db)):
    items = MenuService(MenuRepository(db)).get_category(category_id)
    return [_as_dict(item) for item in items]


@router.post("/items")
def create_menu_item(
    payload: MenuItemCreate,
    current_user: User = Depends(require_role("admin", "cook")),
    db: Session = Depends(get_db),
):
    try:
        item = MenuService(MenuRepository(db)).create_item(
            payload.name, payload.price, payload.category_id
        )
    except MenuItemNameExistsError as exc:
        raise HTTPException(status_code=400, detail="Блюдо с таким названием уже существует") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"status": "success", "item_id": item.id}


@router.patch("/items/{item_id}")
def update_menu_item(
    item_id: int,
    payload: MenuItemUpdate,
    current_user: User = Depends(require_role("admin", "cook")),
    db: Session = Depends(get_db),
):
    try:
        item = MenuService(MenuRepository(db)).update_item(
            item_id,
            payload.name,
            payload.price,
            payload.is_available,
            payload.category_id,
        )
    except MenuItemNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Блюдо не найдено") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"status": "success", "item_id": item.id}

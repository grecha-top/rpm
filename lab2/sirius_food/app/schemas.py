"""
Pydantic-схемы для валидации входных и выходных данных.
"""
from typing import Optional

from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    phone: Optional[str] = None


class UserResponse(BaseModel):
    id: int
    email: str
    balance: float

    class Config:
        from_attributes = True


class MenuItemCreate(BaseModel):
    name: str
    price: float
    category_id: Optional[int] = None


class MenuItemUpdate(BaseModel):
    name: Optional[str] = None
    price: Optional[float] = None
    is_available: Optional[bool] = None
    category_id: Optional[int] = None


class OrderCreate(BaseModel):
    item_id: int
    quantity: int


class DeliveryAssign(BaseModel):
    order_id: int
    courier_id: int


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str

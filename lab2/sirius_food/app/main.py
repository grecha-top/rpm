"""
Точка входа приложения. Выполняет инициализацию FastAPI,
подключение модулей и создание таблиц базы данных.
"""
from fastapi import FastAPI

from app.database import Base, engine
from app.modules.delivery.router import router as delivery_router
from app.modules.menu.router import router as menu_router
from app.modules.orders.router import router as orders_router
from app.modules.users.router import router as users_router

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Sirius.Food API")

app.include_router(users_router, prefix="/users", tags=["users"])
app.include_router(menu_router, prefix="/menu", tags=["menu"])
app.include_router(orders_router, prefix="/orders", tags=["orders"])
app.include_router(delivery_router, prefix="/delivery", tags=["delivery"])

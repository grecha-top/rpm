"""Application entry point and infrastructure wiring."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.database import Base, SessionLocal, engine
from app.models import Role
from app.modules.auth.router import router as auth_router
from app.modules.delivery.router import router as delivery_router
from app.modules.menu.repository import MenuRepository
from app.modules.menu.router import router as menu_router
from app.modules.orders.router import router as orders_router
from app.modules.users.router import router as users_router


Base.metadata.create_all(bind=engine)


def ensure_default_roles() -> None:
    db = SessionLocal()
    try:
        existing = {role.name for role in db.query(Role).all()}
        for name in ("student", "cook", "courier", "admin"):
            if name not in existing:
                db.add(Role(name=name))
        db.commit()
    finally:
        db.close()


def warm_menu_cache() -> None:
    db = SessionLocal()
    try:
        MenuRepository(db).warm_cache()
    finally:
        db.close()


ensure_default_roles()

app = FastAPI(
    title="Sirius.Food API",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(users_router, prefix="/users", tags=["users"])
app.include_router(menu_router, prefix="/menu", tags=["menu"])
app.include_router(orders_router, prefix="/orders", tags=["orders"])
app.include_router(delivery_router, prefix="/delivery", tags=["delivery"])


@app.on_event("startup")
def startup_warm_menu_cache() -> None:
    warm_menu_cache()

"""Application entry point and infrastructure wiring."""
from time import perf_counter

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from app.core.config import settings
from app.core.correlation import correlation_id_middleware, get_correlation_id
from app.core.logging import get_logger, setup_logging
from app.core.observability import setup_sentry, setup_tracing
from app.database import SessionLocal
from app.models import Role
from app.modules.auth.router import router as auth_router
from app.modules.delivery.router import router as delivery_router
from app.modules.menu.repository import MenuRepository
from app.modules.menu.router import router as menu_router
from app.modules.orders.router import router as orders_router
from app.modules.users.router import router as users_router

setup_logging()
setup_sentry()
logger = get_logger(__name__)


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


async def request_logging_middleware(request, call_next):
    started = perf_counter()
    status_code = 500
    if settings.SENTRY_DSN:
        import sentry_sdk

        sentry_sdk.set_tag("correlation_id", get_correlation_id())
    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    except Exception:
        logger.exception(
            "http_request_failed",
            method=request.method,
            path=request.url.path,
        )
        raise
    finally:
        logger.info(
            "http_request_completed",
            method=request.method,
            path=request.url.path,
            status_code=status_code,
            duration_ms=round((perf_counter() - started) * 1000, 2),
            correlation_id=get_correlation_id(),
        )


app.middleware("http")(request_logging_middleware)
app.middleware("http")(correlation_id_middleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["Authorization", "Content-Type", "X-Correlation-ID"],
    expose_headers=["X-Correlation-ID"],
)

app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(users_router, prefix="/users", tags=["users"])
app.include_router(menu_router, prefix="/menu", tags=["menu"])
app.include_router(orders_router, prefix="/orders", tags=["orders"])
app.include_router(delivery_router, prefix="/delivery", tags=["delivery"])

Instrumentator().instrument(app).expose(app, include_in_schema=False)
setup_tracing(app)


@app.get("/debug/sentry", include_in_schema=False)
def trigger_sentry_demo_error() -> None:
    """Generate one controlled error for the observability lab demonstration."""
    if not settings.OBSERVABILITY_DEMO_ENABLED:
        raise HTTPException(status_code=404, detail="Not found")
    raise RuntimeError("Sirius Food observability demo error")


@app.on_event("startup")
def startup_warm_menu_cache() -> None:
    ensure_default_roles()
    warm_menu_cache()

"""Periodic maintenance tasks scheduled by Celery Beat."""
from datetime import date

from sqlalchemy import func

from app.core.celery_app import celery_app
from app.core.redis import redis_client
from app.database import SessionLocal
from app.models import Order


@celery_app.task(name="maintenance.update_order_statistics")
def update_order_statistics() -> dict:
    db = SessionLocal()
    try:
        total = db.query(func.count(Order.id)).scalar() or 0
        paid = db.query(func.count(Order.id)).filter(Order.status == "paid").scalar() or 0
    finally:
        db.close()

    values = {"total": int(total), "paid": int(paid)}
    redis_client.hset(f"statistics:orders:{date.today().isoformat()}", mapping=values)
    return values

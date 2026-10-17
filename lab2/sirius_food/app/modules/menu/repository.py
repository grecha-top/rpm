"""Menu persistence adapter with Cache-Aside Redis acceleration."""
import json
from typing import List, Optional

from redis import RedisError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.redis import redis_client
from app.models import MenuItem


class MenuRepository:
    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def _serialize(item: MenuItem) -> dict:
        return {
            "id": item.id,
            "name": item.name,
            "price": item.price,
            "is_available": item.is_available,
            "category_id": item.category_id,
        }

    @staticmethod
    def _deserialize(data: dict) -> MenuItem:
        return MenuItem(**data)

    def get_all(self) -> List[MenuItem]:
        return self._cached_query(
            "menu:all",
            settings.MENU_CACHE_TTL,
            lambda: self.db.query(MenuItem).order_by(MenuItem.id).all(),
        )

    def get_by_id(self, item_id: int) -> Optional[MenuItem]:
        return self.db.query(MenuItem).filter(MenuItem.id == item_id).first()

    def get_by_name(self, name: str) -> Optional[MenuItem]:
        return self.db.query(MenuItem).filter(MenuItem.name == name).first()

    def get_by_category(self, category_id: int) -> List[MenuItem]:
        key = f"menu:category:{category_id}"
        return self._cached_query(
            key,
            settings.CATEGORY_CACHE_TTL,
            lambda: (
                self.db.query(MenuItem)
                .filter(MenuItem.category_id == category_id)
                .order_by(MenuItem.id)
                .all()
            ),
        )

    def save(self, item: MenuItem) -> MenuItem:
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def create_item(self, name: str, price: float, category_id: Optional[int] = None) -> MenuItem:
        item = MenuItem(
            name=name,
            price=price,
            category_id=category_id,
            is_available=True,
        )
        return self.save(item)

    def invalidate_cache(self, category_id: Optional[int] = None) -> None:
        keys = ["menu:all"]
        if category_id is not None:
            keys.append(f"menu:category:{category_id}")
        try:
            redis_client.delete(*keys)
        except RedisError:
            pass

    def warm_cache(self) -> None:
        self.get_all()

    def _cached_query(self, key: str, ttl: int, loader) -> List[MenuItem]:
        try:
            cached = redis_client.get(key)
            if cached:
                return [self._deserialize(item) for item in json.loads(cached)]

            lock = redis_client.lock(f"{key}:lock", timeout=10, blocking_timeout=10)
            with lock:
                cached = redis_client.get(key)
                if cached:
                    return [self._deserialize(item) for item in json.loads(cached)]
                items = loader()
                value = [self._serialize(item) for item in items]
                redis_client.setex(key, ttl, json.dumps(value))
                return items
        except (RedisError, ValueError, TypeError):
            # Redis is an optimization. A failed cache must fall back to PostgreSQL.
            return loader()

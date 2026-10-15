"""Small Redis-backed rate-limit dependency."""
from typing import Callable

from fastapi import HTTPException, Request
from redis import RedisError

from app.core.redis import redis_client


def rate_limit(max_requests: int = 5, window: int = 60) -> Callable:
    def checker(request: Request) -> None:
        client = request.client.host if request.client else "unknown"
        key = f"rate_limit:{client}:{request.url.path}"
        try:
            current = redis_client.incr(key)
            if current == 1:
                redis_client.expire(key, window)
            if current > max_requests:
                raise HTTPException(status_code=429, detail="Too many requests")
        except RedisError:
            # Redis outage must not make the whole API unavailable.
            return

    return checker

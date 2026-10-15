"""Shared Redis client used by caching and rate limiting."""
import redis

from app.core.config import settings


redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)


def check_redis_connection() -> bool:
    try:
        return bool(redis_client.ping())
    except redis.RedisError:
        return False

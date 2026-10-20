"""Application settings loaded from environment variables and .env."""
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    SECRET_KEY: str = "local-development-secret-change-me"
    DATABASE_URL: str = "postgresql://sirius:sirius@localhost:1432/sirius_food"
    REDIS_URL: str = "redis://localhost:6379/0"
    DEBUG: bool = False
    ALLOWED_ORIGINS: List[str] = []
    ACCESS_TOKEN_MINUTES: int = 15
    REFRESH_TOKEN_DAYS: int = 7
    MENU_CACHE_TTL: int = 300
    CATEGORY_CACHE_TTL: int = 600
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"
    CELERY_TASKS_SYNC: bool = False
    ORDER_TASK_IDEMPOTENCY_TTL: int = 86400
    RABBITMQ_URL: str = "amqp://sirius:sirius@localhost:5672/"
    DELIVERY_GRPC_URL: str = "localhost:50051"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug(cls, value):
        if isinstance(value, str) and value.lower() in {"release", "production", "prod", "false", "0"}:
            return False
        if isinstance(value, str) and value.lower() in {"debug", "development", "dev", "true", "1"}:
            return True
        return value


settings = Settings()

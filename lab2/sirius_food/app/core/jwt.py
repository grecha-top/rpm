"""JWT creation and validation."""
from datetime import datetime, timedelta
from typing import Dict
from uuid import uuid4

from jose import jwt

from app.core.config import settings


ALGORITHM = "HS256"


def create_access_token(user_id: int) -> str:
    now = datetime.utcnow()
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(minutes=settings.ACCESS_TOKEN_MINUTES),
        "type": "access",
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(user_id: int) -> str:
    now = datetime.utcnow()
    payload = {
        "sub": str(user_id),
        "jti": str(uuid4()),
        "iat": now,
        "exp": now + timedelta(days=settings.REFRESH_TOKEN_DAYS),
        "type": "refresh",
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> Dict:
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])

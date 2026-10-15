"""HTTP endpoints for login and refresh-token rotation."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.rate_limit import rate_limit
from app.database import get_db
from app.modules.auth.repository import AuthRepository
from app.modules.auth.service import (
    AuthService,
    InvalidCredentialsError,
    InvalidRefreshTokenError,
)
from app.schemas import LoginRequest, RefreshRequest


router = APIRouter()


@router.post("/login", dependencies=[Depends(rate_limit(5, 60))])
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    try:
        return AuthService(AuthRepository(db)).login(payload.email, payload.password)
    except InvalidCredentialsError as exc:
        raise HTTPException(status_code=401, detail="Invalid email or password") from exc


@router.post("/refresh")
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)):
    try:
        return AuthService(AuthRepository(db)).refresh(payload.refresh_token)
    except InvalidRefreshTokenError as exc:
        raise HTTPException(status_code=401, detail="Invalid refresh token") from exc

"""
Authentication Router

Handles user authentication, registration, and token management.
"""

from datetime import datetime
from uuid import UUID, uuid4
from datetime import timedelta, datetime
from typing import Optional

import jwt
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from ....infrastructure.config.settings import settings
from ....infrastructure.container import ApplicationContainer
from .deps import get_container, get_current_user_id
from ....infrastructure.database.models import UserModel
from sqlalchemy import select
from passlib.context import CryptContext

router = APIRouter()
security = HTTPBearer()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _create_jwt(user_id: UUID, minutes: int, token_type: str = "access") -> str:
    now = datetime.utcnow()
    payload = {
        "sub": str(user_id),
        "typ": token_type,
        "iat": now,
        "exp": now + timedelta(minutes=minutes),
        "iss": "emotionai-api",
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def _parse_jwt(token: str, expected_type: str = "access") -> Optional[UUID]:
    try:
        data = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        if data.get("typ") != expected_type:
            return None
        return UUID(data.get("sub"))
    except Exception:
        return None


@router.post("/register", summary="Register new user")
async def register_user(payload: dict, container: ApplicationContainer = Depends(get_container)):
    email = payload.get("email")
    first_name = payload.get("first_name", "")
    last_name = payload.get("last_name", "")
    password = payload.get("password")
    if not email:
        raise HTTPException(status_code=400, detail="email is required")
    if not password:
        raise HTTPException(status_code=400, detail="password is required")
    db = container.database
    async with db.get_session() as session:
        # naive: create if not exists by email
        existing = await session.execute(select(UserModel).where(UserModel.email == email))
        user = existing.scalar_one_or_none()
        if user is None:
            user = UserModel(
                id=uuid4(),
                email=email,
                hashed_password=pwd_context.hash(password),
                first_name=first_name or "",
                last_name=last_name or "",
                is_active=True,
                is_verified=False,
            )
            session.add(user)
            await session.flush()
        access = _create_jwt(user.id, settings.access_token_expire_minutes, "access")
        refresh = _create_jwt(user.id, getattr(settings, "refresh_token_expire_days", 30) * 24 * 60, "refresh")
        return {
            "access_token": access, "refresh_token": refresh, "token_type": "bearer",
            "expires_in": settings.access_token_expire_minutes * 60,
            "user": {
                "id": str(user.id),
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "is_verified": user.is_verified,
                },
            }


@router.post("/login", summary="User login")
async def login_user(payload: dict, container: ApplicationContainer = Depends(get_container)):
    email = payload.get("email")
    password = payload.get("password")
    if not email:
        raise HTTPException(status_code=400, detail="email is required")
    if not password:
        raise HTTPException(status_code=400, detail="password is required")
    db = container.database
    async with db.get_session() as session:
        res = await session.execute(select(UserModel).where(UserModel.email == email))
        user = res.scalar_one_or_none()
        if user is None or not pwd_context.verify(password, user.hashed_password or ""):
            raise HTTPException(status_code=401, detail="invalid credentials")
        access = _create_jwt(user.id, settings.access_token_expire_minutes, "access")
        refresh = _create_jwt(user.id, getattr(settings, "refresh_token_expire_days", 30) * 24 * 60, "refresh")
        return {
            "access_token": access, "refresh_token": refresh, "token_type": "bearer",
            "expires_in": settings.access_token_expire_minutes * 60,
             "user": {
                "id": str(user.id),
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "is_verified": user.is_verified,
            },
        }

@router.post("/refresh", summary="Refresh access token")
async def refresh_token(payload: dict):
    token = payload.get("refresh_token")
    user_id = _parse_jwt(token or "", expected_type="refresh")
    if not user_id:
        raise HTTPException(status_code=401, detail="invalid refresh token")
    access = _create_jwt(user_id, settings.access_token_expire_minutes, "access")
    return {"access_token": access, "token_type": "bearer", "expires_in": settings.access_token_expire_minutes * 60}

@router.post("/logout", summary="User logout")
async def logout_user(token: str = Depends(security)):
    """Logout user and invalidate token"""
    
    # TODO: Implement token invalidation
    
    return {"message": "Successfully logged out"}


@router.get("/me", summary="Get current user")
async def get_current_user(
    user_id: UUID = Depends(get_current_user_id),
    container: ApplicationContainer = Depends(get_container),
):
    db = container.database
    async with db.get_session() as session:
        res = await session.execute(select(UserModel).where(UserModel.id == user_id))
        user = res.scalar_one_or_none()
        if user is None:
            raise HTTPException(status_code=404, detail="user not found")
        return {
            "id": str(user.id),
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "is_verified": user.is_verified,
            "created_at": (user.created_at.isoformat() if hasattr(user, 'created_at') and user.created_at else None),
        }
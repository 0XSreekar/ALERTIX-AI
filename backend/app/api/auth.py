"""Local auth endpoints — POST /api/auth/signup, /api/auth/login, /api/auth/me.
Uses bcrypt + HS256 JWT. No Supabase required for local dev."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import bcrypt
from fastapi import APIRouter, Depends, HTTPException
from jose import jwt
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_session

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _hash(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def _verify(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())

JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 72


def _make_token(user_id: str, email: str, role: str) -> str:
    settings = get_settings()
    secret = settings.supabase_jwt_secret or "local-dev-secret-change-in-prod"
    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "exp": datetime.now(UTC) + timedelta(hours=JWT_EXPIRE_HOURS),
        "iat": datetime.now(UTC),
    }
    return jwt.encode(payload, secret, algorithm=JWT_ALGORITHM)


class SignupRequest(BaseModel):
    email: str
    password: str
    full_name: str = ""


class LoginRequest(BaseModel):
    email: str
    password: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str
    full_name: str
    role: str


@router.post("/signup", response_model=AuthResponse)
async def signup(body: SignupRequest, session: AsyncSession = Depends(get_session)) -> AuthResponse:
    # Check if email already exists
    existing = await session.execute(
        text("SELECT user_id FROM profiles WHERE email = :email"),
        {"email": body.email.lower()},
    )
    if existing.fetchone():
        raise HTTPException(status_code=409, detail="Email already registered")

    user_id = str(uuid.uuid4())
    hashed = _hash(body.password)
    role = "citizen"

    conn = await session.connection()
    await conn.exec_driver_sql(
        "INSERT INTO profiles (user_id, email, full_name, role, password_hash) "
        "VALUES ($1, $2, $3, $4, $5)",
        (user_id, body.email.lower(), body.full_name, role, hashed),
    )
    await session.commit()

    token = _make_token(user_id, body.email.lower(), role)
    return AuthResponse(
        access_token=token,
        user_id=user_id,
        email=body.email.lower(),
        full_name=body.full_name,
        role=role,
    )


@router.post("/login", response_model=AuthResponse)
async def login(body: LoginRequest, session: AsyncSession = Depends(get_session)) -> AuthResponse:
    result = await session.execute(
        text("SELECT user_id, email, full_name, role, password_hash FROM profiles WHERE email = :email"),
        {"email": body.email.lower()},
    )
    row = result.fetchone()
    if not row or not row.password_hash:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not _verify(body.password, row.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = _make_token(str(row.user_id), row.email, row.role)
    return AuthResponse(
        access_token=token,
        user_id=str(row.user_id),
        email=row.email,
        full_name=row.full_name or "",
        role=row.role,
    )


@router.get("/me")
async def me(session: AsyncSession = Depends(get_session)) -> dict:
    return {"message": "use Authorization: Bearer <token> — JWT decode via auth deps"}

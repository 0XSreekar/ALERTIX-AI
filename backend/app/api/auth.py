"""Local auth endpoints — POST /api/auth/signup, /api/auth/login, /api/auth/me.

Issues a bcrypt-checked HS256 JWT in an HttpOnly, SameSite=Lax cookie
(`alertix_token`). For WebSocket upgrades the browser cannot rely on the
cookie cross-origin, so /api/auth/ws-ticket exchanges the cookie for a
short-lived (60s) bearer token the frontend appends to ?token=.
"""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated

import bcrypt
import jwt
from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_jwt_secret, get_settings
from app.db import get_session
from app.logging import get_logger
from app.redis_client import get_redis

AUTH_COOKIE_NAME = "alertix_token"
_WS_TICKET_TTL_SECONDS = 60

log = get_logger(__name__)

_LOGIN_ATTEMPT_KEY = "login_attempts:{email}"
_LOGIN_LOCKOUT_KEY = "login_lockout:{email}"
_MAX_ATTEMPTS = 5
_LOCKOUT_SECONDS = 15 * 60  # 15 minutes

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _hash(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def _verify(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 72


def _make_token(
    user_id: str,
    email: str,
    role: str,
    *,
    expires_in: timedelta | None = None,
    scope: str = "session",
) -> str:
    """Issue a signed HS256 JWT. `scope=session` is the standard auth token;
    `scope=ws` is a short-lived ticket used to authenticate WebSocket upgrades."""
    secret = get_jwt_secret()
    ttl = expires_in or timedelta(hours=JWT_EXPIRE_HOURS)
    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "scope": scope,
        "exp": datetime.now(UTC) + ttl,
        "iat": datetime.now(UTC),
    }
    return jwt.encode(payload, secret, algorithm=JWT_ALGORITHM)


def _set_auth_cookie(response: Response, token: str) -> None:
    """Set the auth cookie. HttpOnly so JS cannot read it (mitigates XSS token theft).
    Secure in production; SameSite=Lax allows normal navigations but blocks CSRF
    from cross-site form posts."""
    settings = get_settings()
    response.set_cookie(
        key=AUTH_COOKIE_NAME,
        value=token,
        max_age=JWT_EXPIRE_HOURS * 3600,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        path="/",
    )


def _clear_auth_cookie(response: Response) -> None:
    settings = get_settings()
    response.delete_cookie(
        key=AUTH_COOKIE_NAME,
        path="/",
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
    )


def _validate_password_strength(password: str) -> None:
    """Raise HTTPException 422 if password does not meet strength requirements."""
    errors: list[str] = []
    if len(password) < 8:
        errors.append("at least 8 characters")
    if not re.search(r"[A-Z]", password):
        errors.append("at least one uppercase letter")
    if not re.search(r"[a-z]", password):
        errors.append("at least one lowercase letter")
    if not re.search(r"\d", password):
        errors.append("at least one digit")
    if errors:
        raise HTTPException(
            status_code=422,
            detail=f"Password must contain: {', '.join(errors)}.",
        )


async def _check_lockout(email: str, response: Response) -> None:
    """Raise 429 if the account is locked out due to too many failed login attempts."""
    redis = get_redis()
    lockout_key = _LOGIN_LOCKOUT_KEY.format(email=email)
    locked = await redis.get(lockout_key)
    if locked:
        ttl = await redis.ttl(lockout_key)
        response.headers["Retry-After"] = str(max(ttl, 0))
        raise HTTPException(
            status_code=429,
            detail="Account temporarily locked due to too many failed login attempts. Try again later.",
        )


async def _record_failed_login(email: str, response: Response) -> None:
    """Increment failed login counter; lock account after MAX_ATTEMPTS."""
    redis = get_redis()
    attempt_key = _LOGIN_ATTEMPT_KEY.format(email=email)
    lockout_key = _LOGIN_LOCKOUT_KEY.format(email=email)
    count = await redis.incr(attempt_key)
    # Keep counter alive for the lockout window so it doesn't accumulate forever
    await redis.expire(attempt_key, _LOCKOUT_SECONDS)
    if count >= _MAX_ATTEMPTS:
        await redis.set(lockout_key, "1", ex=_LOCKOUT_SECONDS)
        await redis.delete(attempt_key)
        response.headers["Retry-After"] = str(_LOCKOUT_SECONDS)
        raise HTTPException(
            status_code=429,
            detail="Account locked for 15 minutes after too many failed login attempts.",
        )


async def _clear_failed_logins(email: str) -> None:
    """Clear failed-login counters on successful authentication."""
    redis = get_redis()
    await redis.delete(_LOGIN_ATTEMPT_KEY.format(email=email))
    await redis.delete(_LOGIN_LOCKOUT_KEY.format(email=email))


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
async def signup(
    body: SignupRequest,
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> AuthResponse:
    # Validate password strength before anything else
    _validate_password_strength(body.password)

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

    await session.execute(
        text(
            "INSERT INTO profiles (user_id, email, full_name, role, password_hash) "
            "VALUES (:user_id, :email, :full_name, :role, :password_hash)"
        ),
        {
            "user_id": user_id,
            "email": body.email.lower(),
            "full_name": body.full_name,
            "role": role,
            "password_hash": hashed,
        },
    )
    await session.commit()

    token = _make_token(user_id, body.email.lower(), role)
    _set_auth_cookie(response, token)
    return AuthResponse(
        access_token=token,
        user_id=user_id,
        email=body.email.lower(),
        full_name=body.full_name,
        role=role,
    )


@router.post("/login", response_model=AuthResponse)
async def login(
    body: LoginRequest,
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> AuthResponse:
    # Check lockout before doing any DB work
    await _check_lockout(body.email.lower(), response)

    result = await session.execute(
        text(
            "SELECT user_id, email, full_name, role, password_hash FROM profiles WHERE email = :email"
        ),
        {"email": body.email.lower()},
    )
    row = result.fetchone()
    if not row or not row.password_hash:
        await _record_failed_login(body.email.lower(), response)
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not _verify(body.password, row.password_hash):
        await _record_failed_login(body.email.lower(), response)
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # Clear failed-login counters on success
    await _clear_failed_logins(body.email.lower())

    token = _make_token(str(row.user_id), row.email, row.role)
    _set_auth_cookie(response, token)
    return AuthResponse(
        access_token=token,
        user_id=str(row.user_id),
        email=row.email,
        full_name=row.full_name or "",
        role=row.role,
    )


class MeResponse(BaseModel):
    user_id: str
    email: str | None
    role: str
    full_name: str


@router.get("/me", response_model=MeResponse)
async def me(
    session: AsyncSession = Depends(get_session),
    authorization: Annotated[str | None, Header()] = None,
    alertix_token: Annotated[str | None, Cookie()] = None,
) -> MeResponse:
    from app.auth.deps import _decode_jwt, _extract_bearer, _from_payload

    token = _extract_bearer(authorization) or alertix_token
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    payload = _decode_jwt(token)
    user = _from_payload(payload)

    result = await session.execute(
        text("SELECT full_name FROM profiles WHERE user_id = :uid"),
        {"uid": user.user_id},
    )
    row = result.fetchone()
    return MeResponse(
        user_id=user.user_id,
        email=user.email,
        role=user.role,
        full_name=row.full_name if row else "",
    )


@router.post("/logout")
async def logout(response: Response) -> dict:
    """Clear the auth cookie. Idempotent — safe to call when already logged out."""
    _clear_auth_cookie(response)
    return {"status": "logged_out"}


class WsTicketResponse(BaseModel):
    token: str
    expires_in: int


@router.post("/ws-ticket", response_model=WsTicketResponse)
async def ws_ticket(
    authorization: Annotated[str | None, Header()] = None,
    alertix_token: Annotated[str | None, Cookie()] = None,
) -> WsTicketResponse:
    """Exchange the session cookie for a 60s WebSocket auth ticket.

    Browsers don't send cookies on cross-origin WS handshakes reliably, so
    the frontend calls this first then appends ?token=<ticket> to the WS URL.
    The ticket has scope='ws' and a 60s TTL so it can't be replayed for HTTP."""
    from app.auth.deps import _decode_jwt, _extract_bearer, _from_payload

    token = _extract_bearer(authorization) or alertix_token
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    payload = _decode_jwt(token)
    if payload.get("scope") == "ws":
        # Don't let a ws ticket mint another ws ticket — must come from session token
        raise HTTPException(status_code=403, detail="Cannot mint ticket from ws ticket")
    user = _from_payload(payload)
    ticket = _make_token(
        user.user_id,
        user.email or "",
        user.role,
        expires_in=timedelta(seconds=_WS_TICKET_TTL_SECONDS),
        scope="ws",
    )
    return WsTicketResponse(token=ticket, expires_in=_WS_TICKET_TTL_SECONDS)

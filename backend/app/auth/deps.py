"""Auth dependencies — decode local HS256 JWT (issued by /api/auth/login)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

import jwt
from fastapi import Depends, Header, HTTPException, status

from app.config import get_settings


@dataclass(frozen=True)
class CurrentUser:
    user_id: str
    email: str | None
    role: str  # 'citizen' | 'official' | 'admin'


def _jwt_secret() -> str:
    return get_settings().supabase_jwt_secret or "local-dev-secret-change-in-prod"


def _decode_jwt(token: str) -> dict:
    """Verify a locally-issued HS256 JWT (issued by /api/auth/login or /signup)."""
    try:
        return jwt.decode(token, _jwt_secret(), algorithms=["HS256"])
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired"
        ) from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        ) from exc


def _extract_bearer(authorization: str | None) -> str | None:
    if not authorization:
        return None
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    return parts[1].strip()


def _from_payload(payload: dict) -> CurrentUser:
    return CurrentUser(
        user_id=payload["sub"],
        email=payload.get("email"),
        role=payload.get("role", "citizen"),
    )


async def current_user(
    authorization: Annotated[str | None, Header()] = None,
) -> CurrentUser:
    token = _extract_bearer(authorization)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    return _from_payload(_decode_jwt(token))


async def current_user_optional(
    authorization: Annotated[str | None, Header()] = None,
) -> CurrentUser | None:
    token = _extract_bearer(authorization)
    if not token:
        return None
    try:
        return _from_payload(_decode_jwt(token))
    except HTTPException:
        return None


def require_role(*roles: str):
    """Dependency factory restricting access to specific roles."""
    allowed = set(roles)

    async def _checker(user: CurrentUser = Depends(current_user)) -> CurrentUser:
        if user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{user.role}' not permitted",
            )
        return user

    return _checker


async def verify_cron_token(
    x_cron_token: Annotated[str | None, Header(alias="X-Cron-Token")] = None,
) -> None:
    """Internal-endpoint guard for GitHub-Actions-triggered cron jobs."""
    if not x_cron_token or x_cron_token != get_settings().cron_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid cron token")

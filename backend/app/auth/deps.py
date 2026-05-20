from dataclasses import dataclass
from typing import Annotated

import jwt
from fastapi import Depends, Header, HTTPException, status

from app.config import get_settings

settings = get_settings()


@dataclass(frozen=True)
class CurrentUser:
    user_id: str
    email: str | None
    role: str  # 'citizen' | 'official' | 'admin'


def _decode_supabase_jwt(token: str) -> dict:
    """Verify a Supabase-issued JWT using the project's JWT secret (HS256)."""
    if not settings.supabase_jwt_secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Supabase JWT secret not configured",
        )
    try:
        return jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",
        )
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


async def current_user(
    authorization: Annotated[str | None, Header()] = None,
) -> CurrentUser:
    token = _extract_bearer(authorization)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token"
        )
    payload = _decode_supabase_jwt(token)
    return CurrentUser(
        user_id=payload["sub"],
        email=payload.get("email"),
        role=(payload.get("user_metadata") or {}).get("role", "citizen"),
    )


async def current_user_optional(
    authorization: Annotated[str | None, Header()] = None,
) -> CurrentUser | None:
    token = _extract_bearer(authorization)
    if not token:
        return None
    try:
        payload = _decode_supabase_jwt(token)
    except HTTPException:
        return None
    return CurrentUser(
        user_id=payload["sub"],
        email=payload.get("email"),
        role=(payload.get("user_metadata") or {}).get("role", "citizen"),
    )


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
    if not x_cron_token or x_cron_token != settings.cron_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid cron token"
        )

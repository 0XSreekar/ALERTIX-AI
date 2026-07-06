"""Async DB engine.

NOTE: On Windows hosts with broken IPv6, asyncpg fails because it depends on
Python's `socket.getaddrinfo` which silently refuses to resolve IPv6-only
hosts (Supabase's free-tier direct DB host is IPv6-only). psycopg3 in async
mode delegates DNS to `libpq`, which has its own resolver and works fine.
We pick the driver automatically; in production on Render/Linux either driver
works and we default to whatever the URL says.
"""
from __future__ import annotations

import platform
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings

settings = get_settings()


def _async_url() -> str:
    """Return the async URL, swapping asyncpg→psycopg on Windows for libpq DNS."""
    url = settings.database_url
    if platform.system() == "Windows" and url.startswith("postgresql+asyncpg://"):
        # Convert to psycopg3 async dialect and translate ssl=require → sslmode=require
        url = url.replace("postgresql+asyncpg://", "postgresql+psycopg://", 1)
        url = url.replace("ssl=require", "sslmode=require")
        url = url.replace("ssl=true", "sslmode=require")
    return url


engine = create_async_engine(
    _async_url(),
    pool_pre_ping=True,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_timeout=settings.db_pool_timeout,
    pool_recycle=settings.db_pool_recycle_seconds,
    echo=False,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    expire_on_commit=False,
    class_=AsyncSession,
)


class Base(DeclarativeBase):
    """Common declarative base for all ORM models."""


async_session_factory = AsyncSessionLocal


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency yielding a transactional async session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except BaseException:
            await session.rollback()
            raise

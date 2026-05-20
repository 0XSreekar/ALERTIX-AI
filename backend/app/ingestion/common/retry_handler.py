"""Async retry helpers for live data ingestion."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from random import random
from typing import TypeVar

import httpx

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class RetryConfig:
    attempts: int = 3
    base_delay_seconds: float = 0.5
    max_delay_seconds: float = 8.0
    jitter_seconds: float = 0.25


class RetryExhaustedError(RuntimeError):
    """Raised after all retry attempts fail."""


async def retry_async(
    operation: Callable[[], Awaitable[T]],
    *,
    config: RetryConfig = RetryConfig(),
    retry_on: tuple[type[BaseException], ...] = (
        httpx.HTTPError,
        TimeoutError,
        asyncio.TimeoutError,
    ),
) -> T:
    last_error: BaseException | None = None
    for attempt in range(1, config.attempts + 1):
        try:
            return await operation()
        except retry_on as exc:
            last_error = exc
            if attempt >= config.attempts:
                break
            delay = min(config.max_delay_seconds, config.base_delay_seconds * (2 ** (attempt - 1)))
            delay += random() * config.jitter_seconds
            await asyncio.sleep(delay)
    raise RetryExhaustedError(str(last_error)) from last_error

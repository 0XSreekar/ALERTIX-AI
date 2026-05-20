"""Deterministic source-key helpers used before DB upserts."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from datetime import datetime
from typing import Any, TypeVar

T = TypeVar("T")


def source_event_key(source: str, source_event_id: str) -> str:
    return f"{source}:{source_event_id}"


def stable_payload_id(prefix: str, payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return f"{prefix}_{hashlib.sha256(canonical.encode()).hexdigest()[:24]}"


def timestamp_bucket_id(prefix: str, *parts: object, timestamp: datetime) -> str:
    safe_parts = [str(part).strip().lower().replace(" ", "_") for part in parts if part is not None]
    return "_".join([prefix, *safe_parts, timestamp.strftime("%Y%m%d%H%M")])


def unique_by_source_event_id(
    items: list[T], key_getter: Callable[[T], str]
) -> tuple[list[T], int]:
    seen: set[str] = set()
    unique: list[T] = []
    duplicates = 0
    for item in items:
        key = key_getter(item)
        if key in seen:
            duplicates += 1
            continue
        seen.add(key)
        unique.append(item)
    return unique, duplicates

"""Structured ingestion logging helpers."""

from __future__ import annotations

from app.logging import get_logger


def get_ingestion_logger(name: str):
    return get_logger(f"app.ingestion.{name}")


def log_ingestion_summary(log, source: str, **stats: object) -> None:
    log.info("ingestion_complete", source=source, **stats)


def log_malformed_payload(log, source: str, reason: str, **context: object) -> None:
    log.warning("ingestion_malformed_payload", source=source, reason=reason, **context)


def log_duplicate_payload(log, source: str, count: int) -> None:
    if count:
        log.info("ingestion_duplicates_dropped", source=source, count=count)

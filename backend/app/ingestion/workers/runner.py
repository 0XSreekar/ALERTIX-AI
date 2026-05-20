"""Reusable worker entrypoints for scheduled ingestion."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from sqlalchemy.ext.asyncio import AsyncSession

from app.ingestion.common.logger import get_ingestion_logger

log = get_ingestion_logger("workers")

IngestionJob = Callable[[AsyncSession], Awaitable[dict]]


async def run_ingestion_job(name: str, session: AsyncSession, job: IngestionJob) -> dict:
    try:
        result = await job(session)
        log.info("ingestion_worker_success", job=name, result=result)
        return result
    except Exception as exc:
        log.exception("ingestion_worker_failed", job=name, error=str(exc))
        raise

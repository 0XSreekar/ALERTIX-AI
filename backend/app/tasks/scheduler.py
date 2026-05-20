"""APScheduler background jobs for periodic ingestion.

In production, ingestion is triggered externally by GitHub Actions cron.
This scheduler is for local dev convenience — runs inside the FastAPI process.
"""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.config import get_settings
from app.db import AsyncSessionLocal
from app.ingestion.usgs import ingest_usgs
from app.logging import get_logger

log = get_logger(__name__)
scheduler = AsyncIOScheduler()


async def _run_usgs():
    async with AsyncSessionLocal() as session:
        try:
            stats = await ingest_usgs(session, feed="all_hour")
            log.info("scheduler_usgs_done", **stats)
        except Exception as exc:
            log.error("scheduler_usgs_error", error=str(exc))


def start_scheduler():
    settings = get_settings()
    if settings.is_production:
        log.info("scheduler_skip_production")
        return

    scheduler.add_job(
        _run_usgs,
        trigger=IntervalTrigger(seconds=60),
        id="usgs_ingestion",
        replace_existing=True,
    )
    scheduler.start()
    log.info("scheduler_started")


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)
        log.info("scheduler_stopped")

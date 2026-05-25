"""APScheduler background jobs for periodic ingestion.

In production, ingestion is triggered externally by GitHub Actions cron.
This scheduler is for local dev convenience — runs inside the FastAPI process.
"""

import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.config import get_settings
from app.db import AsyncSessionLocal
from app.ingestion.cyclone.service import ingest_cyclones
from app.ingestion.flood.service import ingest_cwc
from app.ingestion.usgs import ingest_usgs
from app.ingestion.weather.service import ingest_weather
from app.ingestion.wildfire.service import ingest_firms
from app.logging import get_logger
from app.tasks.llm_worker import process_pending_alerts

log = get_logger(__name__)
scheduler = AsyncIOScheduler()


async def _run_usgs() -> None:
    async with AsyncSessionLocal() as session:
        try:
            stats = await ingest_usgs(session, feed="all_hour")
            log.info("scheduler_usgs_done", **stats)
        except httpx.HTTPError as exc:
            log.error("scheduler_usgs_http_error", error=str(exc))
        except Exception:
            log.exception("scheduler_usgs_error")


async def _run_firms() -> None:
    """Ingest NASA FIRMS wildfire hotspots for India (VIIRS_SNPP_NRT, 1-day)."""
    async with AsyncSessionLocal() as session:
        try:
            stats = await ingest_firms(session, day_range=1)
            log.info("scheduler_firms_done", **stats)
        except httpx.HTTPError as exc:
            log.error("scheduler_firms_http_error", error=str(exc))
        except Exception:
            log.exception("scheduler_firms_error")


async def _run_cwc() -> None:
    """Ingest CWC river-gauge flood data for India."""
    async with AsyncSessionLocal() as session:
        try:
            stats = await ingest_cwc(session)
            log.info("scheduler_cwc_done", **stats)
        except httpx.HTTPError as exc:
            log.error("scheduler_cwc_http_error", error=str(exc))
        except Exception:
            log.exception("scheduler_cwc_error")


async def _run_weather() -> None:
    """Ingest Open-Meteo weather data for configured India grid points."""
    async with AsyncSessionLocal() as session:
        try:
            stats = await ingest_weather(session)
            log.info("scheduler_weather_done", **stats)
        except httpx.HTTPError as exc:
            log.error("scheduler_weather_http_error", error=str(exc))
        except Exception:
            log.exception("scheduler_weather_error")


async def _run_cyclones() -> None:
    """Ingest IMD/JTWC cyclone track data."""
    async with AsyncSessionLocal() as session:
        try:
            stats = await ingest_cyclones(session)
            log.info("scheduler_cyclones_done", **stats)
        except httpx.HTTPError as exc:
            log.error("scheduler_cyclones_http_error", error=str(exc))
        except Exception:
            log.exception("scheduler_cyclones_error")


async def _run_llm_explanations() -> None:
    """Backfill plain-language explanations for pending alerts via LLM ladder."""
    try:
        stats = await process_pending_alerts()
        if stats["processed"]:
            log.info("scheduler_llm_done", **stats)
    except Exception:
        log.exception("scheduler_llm_error")


def start_scheduler() -> None:
    settings = get_settings()
    if settings.is_production:
        log.info("scheduler_skip_production")
        return

    # USGS earthquakes — every 60 s (near-real-time feed)
    scheduler.add_job(
        _run_usgs,
        trigger=IntervalTrigger(seconds=60),
        id="usgs_ingestion",
        replace_existing=True,
    )

    # NASA FIRMS wildfire hotspots — every 15 min (NRT product refreshes hourly)
    scheduler.add_job(
        _run_firms,
        trigger=IntervalTrigger(minutes=15),
        id="firms_ingestion",
        replace_existing=True,
    )

    # CWC flood / river-gauge — every 30 min
    scheduler.add_job(
        _run_cwc,
        trigger=IntervalTrigger(minutes=30),
        id="cwc_ingestion",
        replace_existing=True,
    )

    # Open-Meteo weather grid — every 60 min
    scheduler.add_job(
        _run_weather,
        trigger=IntervalTrigger(minutes=60),
        id="weather_ingestion",
        replace_existing=True,
    )

    # IMD/JTWC cyclone tracks — every 30 min
    scheduler.add_job(
        _run_cyclones,
        trigger=IntervalTrigger(minutes=30),
        id="cyclone_ingestion",
        replace_existing=True,
    )

    # LLM explanation backfill — every 30 s (small batches)
    scheduler.add_job(
        _run_llm_explanations,
        trigger=IntervalTrigger(seconds=30),
        id="llm_explanations",
        replace_existing=True,
    )

    scheduler.start()
    log.info(
        "scheduler_started",
        jobs=["usgs", "firms", "cwc", "weather", "cyclones", "llm_explanations"],
    )


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
        log.info("scheduler_stopped")

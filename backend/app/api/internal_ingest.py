"""Internal ingestion endpoints — triggered by GitHub Actions cron.

All require X-Cron-Token header.
"""

from fastapi import APIRouter, Depends

from app.auth.deps import verify_cron_token
from app.db import AsyncSession, get_session
from app.ingestion.cyclone.service import ingest_cyclones
from app.ingestion.earthquake.service import ingest_usgs
from app.ingestion.flood.service import ingest_cwc, ingest_flood
from app.ingestion.weather.service import ingest_weather
from app.ingestion.wildfire.service import ingest_firms

router = APIRouter(prefix="/internal/ingest", tags=["internal"])


@router.post("/usgs", dependencies=[Depends(verify_cron_token)])
async def trigger_usgs(
    feed: str = "all_hour",
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await ingest_usgs(session, feed)


@router.post("/firms", dependencies=[Depends(verify_cron_token)])
async def trigger_firms(
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await ingest_firms(session)


@router.post("/imd", dependencies=[Depends(verify_cron_token)])
async def trigger_imd(
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await ingest_cyclones(session)


@router.post("/cwc", dependencies=[Depends(verify_cron_token)])
async def trigger_cwc(
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await ingest_cwc(session)


@router.post("/flood", dependencies=[Depends(verify_cron_token)])
async def trigger_flood(
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await ingest_flood(session)


@router.post("/weather", dependencies=[Depends(verify_cron_token)])
async def trigger_weather(
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await ingest_weather(session)


@router.post("/cyclones", dependencies=[Depends(verify_cron_token)])
async def trigger_cyclones(
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await ingest_cyclones(session)

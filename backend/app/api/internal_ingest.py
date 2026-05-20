"""Internal ingestion endpoints — triggered by GitHub Actions cron.

All require X-Cron-Token header.
"""

from fastapi import APIRouter, Depends

from app.auth.deps import verify_cron_token
from app.db import AsyncSession, get_session
from app.ingestion.usgs import ingest_usgs
from app.ingestion.nasa_firms import ingest_firms
from app.ingestion.imd_cyclone import ingest_imd
from app.ingestion.cwc import ingest_cwc
from app.ingestion.google_flood_hub import ingest_google_flood_hub

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
    return await ingest_imd(session)


@router.post("/cwc", dependencies=[Depends(verify_cron_token)])
async def trigger_cwc(
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await ingest_cwc(session)


@router.post("/google_flood_hub", dependencies=[Depends(verify_cron_token)])
async def trigger_google_flood_hub(
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await ingest_google_flood_hub(session)

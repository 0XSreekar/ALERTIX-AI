"""Backfill USGS earthquake catalog for the Indian subcontinent (5+ years).

Usage: python -m scripts.backfill_usgs
"""

import asyncio

from app.db import AsyncSessionLocal
from app.ingestion.usgs import ingest_usgs


async def main():
    async with AsyncSessionLocal() as session:
        for feed in ["all_day"]:
            stats = await ingest_usgs(session, feed=feed)
            print(f"Feed {feed}: {stats}")


if __name__ == "__main__":
    asyncio.run(main())

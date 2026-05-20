"""Backward-compatible imports for cyclone ingestion."""

from app.ingestion.cyclone.client import fetch_imd_bulletins, fetch_jtwc_bulletins
from app.ingestion.cyclone.parser import CycloneParser, ForecastNormalizer, StormTracker
from app.ingestion.cyclone.service import ingest_cyclones

ingest_imd = ingest_cyclones

__all__ = [
    "CycloneParser",
    "ForecastNormalizer",
    "StormTracker",
    "fetch_imd_bulletins",
    "fetch_jtwc_bulletins",
    "ingest_cyclones",
    "ingest_imd",
]

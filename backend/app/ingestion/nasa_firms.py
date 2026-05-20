"""Backward-compatible imports for India-scoped NASA FIRMS ingestion."""

from app.ingestion.wildfire.client import FIRMS_AREA_URL, FIRMS_SOURCES, fetch_firms_csv
from app.ingestion.wildfire.parser import parse_firms_csv
from app.ingestion.wildfire.service import ingest_firms

__all__ = ["FIRMS_AREA_URL", "FIRMS_SOURCES", "fetch_firms_csv", "ingest_firms", "parse_firms_csv"]

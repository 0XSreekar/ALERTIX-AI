"""Backward-compatible imports for CWC flood ingestion."""

from app.ingestion.flood.client import fetch_cwc_dashboard
from app.ingestion.flood.parser import parse_cwc_gauge_tables
from app.ingestion.flood.service import ingest_cwc, ingest_flood

__all__ = ["fetch_cwc_dashboard", "ingest_cwc", "ingest_flood", "parse_cwc_gauge_tables"]

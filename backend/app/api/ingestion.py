"""Ingestion health and metrics endpoints."""

from fastapi import APIRouter, Response

from app.ingestion.metrics import metrics

router = APIRouter(prefix="/api/ingest", tags=["ingest"])


@router.get("/health")
async def ingest_health() -> dict:
    return {"status": "ok", "ingest": metrics.snapshot()}


@router.get("/metrics")
async def ingest_metrics() -> Response:
    return Response(metrics.prometheus_text(), media_type="text/plain; version=0.0.4")

"""Processing worker health and metrics endpoints."""

from fastapi import APIRouter, Response

from app.processing.metrics import metrics

router = APIRouter(prefix="/api/processing", tags=["processing"])


@router.get("/health")
async def processing_health() -> dict:
    return {"status": "ok", "consumers": metrics.snapshot()}


@router.get("/metrics")
async def processing_metrics() -> Response:
    return Response(metrics.prometheus_text(), media_type="text/plain; version=0.0.4")

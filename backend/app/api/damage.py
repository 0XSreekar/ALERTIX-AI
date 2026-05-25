"""Damage assessment endpoint — classify, segment, persist, list history."""

from __future__ import annotations

import base64
from datetime import datetime
from io import BytesIO
from pathlib import Path
from uuid import UUID

import numpy as np
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from PIL import Image
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import CurrentUser, current_user
from app.config import get_settings
from app.db import get_session
from app.ml.damage_segment import DamageSegmenter
from app.storage import UploadStorage

router = APIRouter(prefix="/api/damage", tags=["damage"])


def _mask_to_png_b64(mask: np.ndarray) -> str:
    """Encode a binary mask as a PNG data-URL (RGBA, transparent outside damage)."""
    if mask.size == 0:
        return ""
    rgba = np.zeros((*mask.shape, 4), dtype=np.uint8)
    # Damaged pixels → solid red with 0.55 alpha; everything else transparent.
    rgba[..., 0] = 239  # R
    rgba[..., 1] = 68  # G
    rgba[..., 2] = 68  # B
    rgba[..., 3] = np.where(mask > 0, 140, 0).astype(np.uint8)
    buf = BytesIO()
    Image.fromarray(rgba, mode="RGBA").save(buf, format="PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


async def _find_nearest_event(
    session: AsyncSession, lat: float | None, lon: float | None
) -> dict | None:
    if lat is None or lon is None:
        return None
    row = (
        await session.execute(
            text("""
                SELECT id, hazard_type, occurred_at,
                       (metadata->>'title')::text AS title,
                       ST_Distance(
                           location::geography,
                           ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography
                       ) AS distance_m
                FROM events
                WHERE location IS NOT NULL
                ORDER BY ST_Distance(
                    location::geography,
                    ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography
                )
                LIMIT 1
            """),
            {"lon": lon, "lat": lat},
        )
    ).fetchone()
    if not row or row.distance_m is None or row.distance_m > 100_000:
        return None
    return {
        "id": str(row.id),
        "hazard_type": row.hazard_type,
        "title": row.title,
        "distance_km": round(row.distance_m / 1000.0, 1),
        "occurred_at": row.occurred_at.isoformat() if row.occurred_at else None,
    }


@router.post("/segment")
async def segment_damage(
    file: UploadFile = File(...),
    latitude: float | None = Form(default=None),
    longitude: float | None = Form(default=None),
    notes: str | None = Form(default=None),
    user: CurrentUser = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    content = await file.read()
    stored = await UploadStorage().store(
        session, content, file.filename or "damage.jpg", user.user_id
    )

    checkpoint = get_settings().damage_model_checkpoint
    if not checkpoint:
        await session.commit()
        raise HTTPException(
            status_code=503,
            detail="Damage model checkpoint is not configured. Upload was stored and deduplicated.",
        )

    try:
        image = Image.open(BytesIO(content)).convert("RGB").resize((256, 256))
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid image upload") from exc

    arr = np.asarray(image, dtype=np.float32).transpose(2, 0, 1) / 255.0
    prediction = DamageSegmenter(checkpoint).predict(arr)
    model_version = Path(checkpoint).name

    nearest = await _find_nearest_event(session, latitude, longitude)

    report_id = (
        await session.execute(
            text("""
                INSERT INTO damage_results
                    (user_id, upload_sha256, class_label, confidence, class_probs,
                     bounding_boxes, model_version, latitude, longitude,
                     nearest_event_id, notes)
                VALUES (:user_id, :sha, :label, :conf, CAST(:probs AS JSONB),
                        CAST(:boxes AS JSONB), :ver, :lat, :lon,
                        :nearest, :notes)
                RETURNING id
            """),
            {
                "user_id": user.user_id,
                "sha": stored.sha256,
                "label": prediction.class_label,
                "conf": prediction.confidence,
                "probs": __import__("json").dumps(prediction.class_probs),
                "boxes": __import__("json").dumps(prediction.bounding_boxes),
                "ver": model_version,
                "lat": latitude,
                "lon": longitude,
                "nearest": nearest["id"] if nearest else None,
                "notes": notes,
            },
        )
    ).scalar_one()
    await session.commit()

    return {
        "status": "processed",
        "report_id": str(report_id),
        "filename": file.filename,
        "sha256": stored.sha256,
        "image_url": f"/api/damage/reports/{report_id}/image",
        "deduplicated": stored.deduplicated,
        "class_label": prediction.class_label,
        "confidence": prediction.confidence,
        "class_probs": prediction.class_probs,
        "bounding_boxes": prediction.bounding_boxes,
        "mask_overlay": _mask_to_png_b64(prediction.mask),
        "mask_shape": list(prediction.mask.shape),
        "model_version": model_version,
        "latency_ms": round(prediction.latency_ms, 1),
        "nearest_event": nearest,
    }


@router.get("/reports")
async def list_damage_reports(
    limit: int = 20,
    user: CurrentUser = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    rows = (
        await session.execute(
            text("""
                SELECT id, upload_sha256, class_label, confidence, class_probs,
                       latitude, longitude, model_version, notes, created_at
                FROM damage_results
                WHERE user_id = :uid
                ORDER BY created_at DESC
                LIMIT :limit
            """),
            {"uid": user.user_id, "limit": min(max(limit, 1), 100)},
        )
    ).fetchall()
    return {
        "reports": [
            {
                "id": str(r.id),
                "class_label": r.class_label,
                "confidence": float(r.confidence),
                "class_probs": r.class_probs or {},
                "latitude": r.latitude,
                "longitude": r.longitude,
                "model_version": r.model_version,
                "notes": r.notes,
                "image_url": f"/api/damage/reports/{r.id}/image",
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]
    }


@router.get("/reports/{report_id}/image")
async def get_damage_image(
    report_id: UUID,
    user: CurrentUser = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> Response:
    row = (
        await session.execute(
            text("""
                SELECT d.upload_sha256, u.path
                FROM damage_results d
                JOIN uploads u ON u.sha256 = d.upload_sha256
                WHERE d.id = :id AND (d.user_id = :uid OR :role IN ('official', 'admin'))
            """),
            {"id": report_id, "uid": user.user_id, "role": user.role},
        )
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Report not found")
    # path may be local filesystem path or a public R2 URL
    if row.path.startswith(("http://", "https://")):
        return Response(status_code=302, headers={"Location": row.path})
    p = Path(row.path)
    if not p.exists():
        raise HTTPException(status_code=410, detail="Image bytes no longer available")
    suffix = p.suffix.lower().lstrip(".") or "jpeg"
    media = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png"}.get(
        suffix, "application/octet-stream"
    )
    data = p.read_bytes()
    return Response(content=data, media_type=media)


_ = datetime  # keep import for future scheduled cleanups

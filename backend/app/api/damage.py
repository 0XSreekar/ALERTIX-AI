"""Damage assessment endpoint."""

from io import BytesIO

import numpy as np
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import CurrentUser, current_user
from app.config import get_settings
from app.db import get_session
from app.ml.damage_segment import DamageSegmenter
from app.storage import UploadStorage

router = APIRouter(prefix="/api/damage", tags=["damage"])


@router.post("/segment")
async def segment_damage(
    file: UploadFile = File(...),
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
    await session.commit()
    return {
        "status": "processed",
        "filename": file.filename,
        "sha256": stored.sha256,
        "path": stored.path,
        "deduplicated": stored.deduplicated,
        "class_label": prediction.class_label,
        "confidence": prediction.confidence,
        "bounding_boxes": prediction.bounding_boxes,
        "model_version": checkpoint,
    }

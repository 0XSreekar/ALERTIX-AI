"""Damage assessment endpoint — POST /api/damage/segment (DeepLabV3)."""

from fastapi import APIRouter, Depends, File, UploadFile

from app.auth.deps import CurrentUser, current_user
from app.ml.damage_segment import segment_image

router = APIRouter(prefix="/api/damage", tags=["damage"])


@router.post("/segment")
async def segment_damage(
    file: UploadFile = File(...),
    user: CurrentUser = Depends(current_user),
) -> dict:
    content = await file.read()
    size_kb = len(content) / 1024

    result = segment_image(content)

    has_classes = bool(result.get("classes"))
    return {
        "status": "analyzed" if has_classes else "unavailable",
        "filename": file.filename,
        "size_kb": round(size_kb, 1),
        **result,
    }

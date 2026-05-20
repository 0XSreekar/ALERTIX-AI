"""Damage assessment endpoint — POST /api/damage/segment.

Phase 1: accepts upload, returns placeholder. Phase 2: runs DeepLabV3."""

from fastapi import APIRouter, Depends, File, UploadFile

from app.auth.deps import CurrentUser, current_user

router = APIRouter(prefix="/api/damage", tags=["damage"])


@router.post("/segment")
async def segment_damage(
    file: UploadFile = File(...),
    user: CurrentUser = Depends(current_user),
) -> dict:
    content = await file.read()
    size_kb = len(content) / 1024

    # Phase 2: run DeepLabV3 segmentation on the image bytes
    # For now, return a placeholder acknowledging the upload.
    return {
        "status": "preview",
        "filename": file.filename,
        "size_kb": round(size_kb, 1),
        "message": "Damage segmentation model will be available in Phase 2. "
        "Image received and stored for future processing.",
        "classes": {},
        "model_version": None,
    }

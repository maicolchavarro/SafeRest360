import io
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_admin
from app.database import get_db
from app.models.model_registry import ModelRecord
from app.models.user import User
from app.services.inference_service import detect_persons as run_detection

router = APIRouter(prefix="/inference", tags=["inference"])


@router.post("/detect")
async def detect_persons(
    file: UploadFile = File(...),
    confidence: float = 0.5,
    user: User = Depends(get_current_user),
):
    """Upload an image and get person detections."""
    contents = await file.read()
    try:
        import numpy as np
        from PIL import Image
        image = Image.open(io.BytesIO(contents)).convert("RGB")
        img_array = np.ascontiguousarray(np.array(image)[:, :, ::-1])  # Ultralytics expects BGR arrays
    except Exception:
        raise HTTPException(status_code=400, detail="Imagen no válida")

    detections = run_detection(img_array, confidence)

    return {
        "image_size": {"width": img_array.shape[1], "height": img_array.shape[0]},
        "detections": detections,
        "count": len(detections),
    }


@router.get("/models")
async def list_models(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ModelRecord).where(ModelRecord.is_active == True).order_by(ModelRecord.created_at.desc())
    )
    models = result.scalars().all()
    return [
        {
            "id": str(m.id),
            "name": m.name,
            "variant": m.variant,
            "version": m.version,
            "status": m.status,
            "metrics": m.metrics,
            "license": m.license,
        }
        for m in models
    ]


@router.post("/models/{model_id}/promote")
async def promote_model(
    model_id: UUID,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ModelRecord).where(ModelRecord.id == model_id))
    model = result.scalar_one_or_none()
    if model is None:
        raise HTTPException(status_code=404, detail="Modelo no encontrado")

    current_prod = await db.execute(
        select(ModelRecord).where(ModelRecord.status == "production")
    )
    for m in current_prod.scalars().all():
        m.status = "archived"

    from datetime import datetime, timezone
    model.status = "production"
    model.promoted_at = datetime.now(timezone.utc)
    await db.commit()
    return {"message": f"Modelo {model.name} promovido a producción"}

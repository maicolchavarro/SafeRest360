from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_admin
from app.database import get_db
from app.models.camera import Camera
from app.models.user import User
from app.schemas.camera import CameraCreate, CameraLiveStatus, CameraResponse, CameraUpdate
from app.services.stream_manager import stream_manager

router = APIRouter(prefix="/cameras", tags=["cameras"])


async def _owned_camera(camera_id: UUID, user: User, db: AsyncSession) -> Camera:
    result = await db.execute(
        select(Camera).where(Camera.id == camera_id, Camera.restaurant_id == user.restaurant_id)
    )
    camera = result.scalar_one_or_none()
    if camera is None:
        raise HTTPException(status_code=404, detail="Cámara no encontrada")
    return camera


@router.get("/{camera_id}/live.jpg")
async def live_frame(
    camera_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _owned_camera(camera_id, user, db)
    worker = stream_manager.get(camera_id)
    if worker is None or worker.latest_jpeg is None:
        raise HTTPException(status_code=404, detail="Sin imagen en vivo")
    return Response(worker.latest_jpeg, media_type="image/jpeg", headers={"Cache-Control": "no-store"})


@router.get("/{camera_id}/live/status", response_model=CameraLiveStatus)
async def live_status(
    camera_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    camera = await _owned_camera(camera_id, user, db)
    worker = stream_manager.get(camera_id)
    if worker is None:
        return CameraLiveStatus(
            streaming=False,
            status=camera.status,
            error=None if camera.rtsp_url else "La cámara no tiene URL de stream",
        )
    return CameraLiveStatus(
        streaming=True,
        status=worker.status,
        persons_in_view=worker.persons_in_view,
        analysis_fps=round(worker.analysis_fps, 1),
        last_frame_at=worker.last_frame_at,
        error=worker.error,
    )


@router.get("", response_model=list[CameraResponse])
async def list_cameras(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Camera)
        .where(Camera.restaurant_id == user.restaurant_id, Camera.is_active == True)
        .order_by(Camera.created_at.desc())
    )
    return result.scalars().all()


@router.post("", response_model=CameraResponse, status_code=status.HTTP_201_CREATED)
async def create_camera(
    body: CameraCreate,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    camera = Camera(restaurant_id=user.restaurant_id, **body.model_dump())
    db.add(camera)
    await db.commit()
    await db.refresh(camera)
    return camera


@router.get("/{camera_id}", response_model=CameraResponse)
async def get_camera(
    camera_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Camera).where(
            Camera.id == camera_id, Camera.restaurant_id == user.restaurant_id
        )
    )
    camera = result.scalar_one_or_none()
    if camera is None:
        raise HTTPException(status_code=404, detail="Cámara no encontrada")
    return camera


@router.patch("/{camera_id}", response_model=CameraResponse)
async def update_camera(
    camera_id: UUID,
    body: CameraUpdate,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Camera).where(
            Camera.id == camera_id, Camera.restaurant_id == user.restaurant_id
        )
    )
    camera = result.scalar_one_or_none()
    if camera is None:
        raise HTTPException(status_code=404, detail="Cámara no encontrada")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(camera, field, value)
    await db.commit()
    await db.refresh(camera)
    return camera


@router.delete("/{camera_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_camera(
    camera_id: UUID,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Camera).where(
            Camera.id == camera_id, Camera.restaurant_id == user.restaurant_id
        )
    )
    camera = result.scalar_one_or_none()
    if camera is None:
        raise HTTPException(status_code=404, detail="Cámara no encontrada")
    camera.is_active = False
    await db.commit()

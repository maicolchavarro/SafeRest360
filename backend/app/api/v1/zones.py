from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_admin
from app.database import get_db
from app.models.camera import Camera
from app.models.user import User
from app.models.zone import Zone
from app.schemas.zone import ZoneCreate, ZoneResponse, ZoneUpdate

router = APIRouter(tags=["zones"])


async def _verify_camera_access(camera_id: UUID, user: User, db: AsyncSession) -> Camera:
    result = await db.execute(
        select(Camera).where(Camera.id == camera_id, Camera.restaurant_id == user.restaurant_id)
    )
    camera = result.scalar_one_or_none()
    if camera is None:
        raise HTTPException(status_code=404, detail="Cámara no encontrada")
    return camera


async def get_owned_zone(zone_id: UUID, user: User, db: AsyncSession) -> Zone:
    result = await db.execute(
        select(Zone)
        .join(Camera, Zone.camera_id == Camera.id)
        .where(Zone.id == zone_id, Camera.restaurant_id == user.restaurant_id)
    )
    zone = result.scalar_one_or_none()
    if zone is None:
        raise HTTPException(status_code=404, detail="Zona no encontrada")
    return zone


@router.get("/cameras/{camera_id}/zones", response_model=list[ZoneResponse])
async def list_zones(
    camera_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _verify_camera_access(camera_id, user, db)
    result = await db.execute(
        select(Zone).where(Zone.camera_id == camera_id, Zone.is_active == True)
    )
    return result.scalars().all()


@router.post("/cameras/{camera_id}/zones", response_model=ZoneResponse, status_code=status.HTTP_201_CREATED)
async def create_zone(
    camera_id: UUID,
    body: ZoneCreate,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    await _verify_camera_access(camera_id, user, db)
    zone = Zone(
        camera_id=camera_id,
        name=body.name,
        zone_type=body.zone_type,
        polygon_points=[p.model_dump() for p in body.polygon_points],
        color=body.color,
    )
    db.add(zone)
    await db.commit()
    await db.refresh(zone)
    return zone


@router.get("/zones/{zone_id}", response_model=ZoneResponse)
async def get_zone(
    zone_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_owned_zone(zone_id, user, db)


@router.patch("/zones/{zone_id}", response_model=ZoneResponse)
async def update_zone(
    zone_id: UUID,
    body: ZoneUpdate,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    zone = await get_owned_zone(zone_id, user, db)
    updates = body.model_dump(exclude_unset=True)
    if "polygon_points" in updates and updates["polygon_points"] is not None:
        updates["polygon_points"] = [p.model_dump() for p in body.polygon_points]
    for field, value in updates.items():
        setattr(zone, field, value)
    await db.commit()
    await db.refresh(zone)
    return zone


@router.delete("/zones/{zone_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_zone(
    zone_id: UUID,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    zone = await get_owned_zone(zone_id, user, db)
    zone.is_active = False
    await db.commit()

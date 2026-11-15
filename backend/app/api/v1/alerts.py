from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.alert import Alert
from app.models.camera import Camera
from app.models.user import User
from app.models.zone import Zone
from app.schemas.alert import AlertResponse, AlertUpdate, DashboardSummary

router = APIRouter(tags=["alerts"])


@router.get("/alerts", response_model=list[AlertResponse])
async def list_alerts(
    status: str | None = Query(None),
    severity: str | None = Query(None),
    camera_id: UUID | None = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(Alert).where(Alert.restaurant_id == user.restaurant_id)
    if status:
        query = query.where(Alert.status == status)
    if severity:
        query = query.where(Alert.severity == severity)
    if camera_id:
        query = query.where(Alert.camera_id == camera_id)
    query = query.order_by(Alert.triggered_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/alerts/{alert_id}", response_model=AlertResponse)
async def get_alert(
    alert_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Alert).where(Alert.id == alert_id, Alert.restaurant_id == user.restaurant_id)
    )
    alert = result.scalar_one_or_none()
    if alert is None:
        raise HTTPException(status_code=404, detail="Alerta no encontrada")
    return alert


@router.patch("/alerts/{alert_id}", response_model=AlertResponse)
async def update_alert(
    alert_id: UUID,
    body: AlertUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Alert).where(Alert.id == alert_id, Alert.restaurant_id == user.restaurant_id)
    )
    alert = result.scalar_one_or_none()
    if alert is None:
        raise HTTPException(status_code=404, detail="Alerta no encontrada")
    now = datetime.now(timezone.utc)
    if body.status == "acknowledged" and alert.status == "new":
        alert.status = "acknowledged"
        alert.acknowledged_at = now
    elif body.status == "resolved":
        alert.status = "resolved"
        alert.resolved_at = now
        alert.resolved_by = body.resolved_by or user.id
    elif body.status == "false_alarm":
        alert.status = "false_alarm"
        alert.resolved_at = now
        alert.resolved_by = user.id
    await db.commit()
    await db.refresh(alert)
    return alert


@router.get("/dashboard/summary", response_model=DashboardSummary)
async def dashboard_summary(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rid = user.restaurant_id

    cam_result = await db.execute(
        select(Camera).where(Camera.restaurant_id == rid, Camera.is_active == True)
    )
    cameras = cam_result.scalars().all()
    total = len(cameras)
    online = sum(1 for c in cameras if c.status == "online")

    from datetime import date
    today_start = datetime.combine(date.today(), datetime.min.time(), tzinfo=timezone.utc)
    alerts_today_result = await db.execute(
        select(func.count(Alert.id)).where(
            Alert.restaurant_id == rid, Alert.triggered_at >= today_start
        )
    )
    alerts_today = alerts_today_result.scalar() or 0

    pending_result = await db.execute(
        select(func.count(Alert.id)).where(
            Alert.restaurant_id == rid, Alert.status == "new"
        )
    )
    alerts_pending = pending_result.scalar() or 0

    zones_result = await db.execute(
        select(func.count(Zone.id))
        .join(Camera, Zone.camera_id == Camera.id)
        .where(Zone.is_active == True, Camera.restaurant_id == rid, Camera.is_active == True)
    )
    zones_count = zones_result.scalar() or 0

    return DashboardSummary(
        total_cameras=total,
        cameras_online=online,
        cameras_offline=total - online,
        alerts_today=alerts_today,
        alerts_pending=alerts_pending,
        zones_configured=zones_count,
    )

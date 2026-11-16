from datetime import datetime, timezone, timedelta
from uuid import UUID

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy import func, select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_admin
from app.config import settings
from app.database import get_db
from app.models.alert import Alert
from app.models.camera import Camera
from app.models.notification import Notification
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


@router.get("/alerts/{alert_id}/snapshot")
async def get_alert_snapshot(
    alert_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Alert).where(Alert.id == alert_id, Alert.restaurant_id == user.restaurant_id)
    )
    alert = result.scalar_one_or_none()
    if alert is None or not alert.snapshot_path or not Path(alert.snapshot_path).is_file():
        raise HTTPException(status_code=404, detail="Imagen no disponible")
    return FileResponse(alert.snapshot_path, media_type="image/jpeg", headers={"Cache-Control": "private, no-store"})


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


def _delete_snapshot(alert: Alert) -> bool:
    """Only remove a snapshot inside this restaurant's storage directory."""
    if not alert.snapshot_path:
        return False
    path = Path(alert.snapshot_path).resolve()
    allowed = (Path(settings.SNAPSHOT_LOCAL_PATH) / str(alert.restaurant_id)).resolve()
    if not path.is_relative_to(allowed):
        raise HTTPException(status_code=409, detail="La imagen no pertenece al almacenamiento del restaurante")
    try:
        path.unlink()
        return True
    except FileNotFoundError:
        return False
    except OSError:
        raise HTTPException(status_code=503, detail="No se pudo eliminar la imagen; la alerta se conserva") from None


@router.delete("/alerts/{alert_id}")
async def delete_alert(
    alert_id: UUID,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Alert).where(Alert.id == alert_id, Alert.restaurant_id == user.restaurant_id)
    )
    alert = result.scalar_one_or_none()
    if alert is None:
        raise HTTPException(status_code=404, detail="Alerta no encontrada")

    file_deleted = _delete_snapshot(alert)

    await db.execute(delete(Notification).where(Notification.alert_id == alert.id))
    await db.delete(alert)
    await db.commit()
    return {"status": "deleted", "id": str(alert_id), "file_deleted": file_deleted,
            "message": "Alerta eliminada correctamente"}


@router.post("/alerts/cleanup")
async def cleanup_alerts(
    older_than_days: int | None = Query(None, ge=1, le=365),
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    days = older_than_days or settings.ALERT_RETENTION_DAYS
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    result = await db.execute(
        select(Alert).where(Alert.restaurant_id == user.restaurant_id, Alert.triggered_at < cutoff)
    )
    alerts_to_delete = result.scalars().all()
    count = 0
    files_deleted = 0

    skipped = 0
    for a in alerts_to_delete:
        try:
            files_deleted += int(_delete_snapshot(a))
        except HTTPException:
            # Keep failed records so an administrator can retry the cleanup.
            skipped += 1
            continue
        await db.execute(delete(Notification).where(Notification.alert_id == a.id))
        await db.delete(a)
        count += 1

    await db.commit()
    return {
        "status": "success",
        "retention_days": days,
        "alerts_deleted": count,
        "files_deleted": files_deleted,
        "alerts_skipped": skipped,
        "message": f"Se eliminaron {count} alertas y {files_deleted} imágenes anteriores a {days} días. " + f"Alertas conservadas por error de archivo: {skipped}."
    }


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

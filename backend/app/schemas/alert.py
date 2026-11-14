from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class AlertUpdate(BaseModel):
    status: str | None = None
    resolved_by: UUID | None = None


class AlertResponse(BaseModel):
    id: UUID
    rule_id: UUID
    camera_id: UUID
    zone_id: UUID
    restaurant_id: UUID
    alert_type: str
    severity: str
    status: str
    description: str | None
    snapshot_path: str | None
    detection_data: dict | None
    triggered_at: datetime
    acknowledged_at: datetime | None
    resolved_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class DashboardSummary(BaseModel):
    total_cameras: int
    cameras_online: int
    cameras_offline: int
    alerts_today: int
    alerts_pending: int
    zones_configured: int

from uuid import UUID

from pydantic import BaseModel

from app.schemas.common import UTCDateTime


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
    has_snapshot: bool
    detection_data: dict | None
    triggered_at: UTCDateTime
    acknowledged_at: UTCDateTime | None
    resolved_at: UTCDateTime | None
    created_at: UTCDateTime

    model_config = {"from_attributes": True}


class DashboardSummary(BaseModel):
    total_cameras: int
    cameras_online: int
    cameras_offline: int
    alerts_today: int
    alerts_pending: int
    zones_configured: int

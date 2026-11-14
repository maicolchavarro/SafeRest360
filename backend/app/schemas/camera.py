from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class CameraCreate(BaseModel):
    name: str
    location_description: str | None = None
    rtsp_url: str | None = None
    stream_type: str = "rtsp"
    resolution_w: int | None = None
    resolution_h: int | None = None
    fps: int = 15


class CameraUpdate(BaseModel):
    name: str | None = None
    location_description: str | None = None
    rtsp_url: str | None = None
    stream_type: str | None = None
    resolution_w: int | None = None
    resolution_h: int | None = None
    fps: int | None = None
    is_active: bool | None = None


class CameraResponse(BaseModel):
    id: UUID
    restaurant_id: UUID
    name: str
    location_description: str | None
    stream_type: str
    resolution_w: int | None
    resolution_h: int | None
    fps: int
    status: str
    last_heartbeat: datetime | None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}

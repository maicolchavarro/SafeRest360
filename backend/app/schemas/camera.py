from datetime import datetime
from urllib.parse import urlparse
from uuid import UUID

from pydantic import BaseModel, field_validator

from app.schemas.common import UTCDateTime


def _check_stream_url(value: str | None) -> str | None:
    if value is None or value.strip() == "":
        return None
    value = value.strip()
    parsed = urlparse(value)
    # the URL is handed to FFmpeg, which would also open local files or other protocols
    if parsed.scheme not in ("rtsp", "rtsps") or not parsed.hostname:
        raise ValueError("La URL del stream debe ser rtsp:// o rtsps:// con un host")
    return value


class CameraCreate(BaseModel):
    name: str
    location_description: str | None = None
    rtsp_url: str | None = None
    stream_type: str = "rtsp"
    resolution_w: int | None = None
    resolution_h: int | None = None
    fps: int = 15

    _validate_url = field_validator("rtsp_url")(_check_stream_url)


class CameraUpdate(BaseModel):
    name: str | None = None
    location_description: str | None = None
    rtsp_url: str | None = None
    stream_type: str | None = None
    resolution_w: int | None = None
    resolution_h: int | None = None
    fps: int | None = None
    is_active: bool | None = None

    _validate_url = field_validator("rtsp_url")(_check_stream_url)


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
    last_heartbeat: UTCDateTime | None
    is_active: bool
    has_stream_url: bool
    created_at: UTCDateTime

    model_config = {"from_attributes": True}


class CameraLiveStatus(BaseModel):
    streaming: bool
    status: str
    persons_in_view: int = 0
    analysis_fps: float = 0.0
    last_frame_at: datetime | None = None
    error: str | None = None

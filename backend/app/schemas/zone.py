from uuid import UUID

from pydantic import BaseModel


class PolygonPoint(BaseModel):
    x: float
    y: float


class ZoneCreate(BaseModel):
    name: str
    zone_type: str
    polygon_points: list[PolygonPoint]
    color: str = "#FF0000"


class ZoneUpdate(BaseModel):
    name: str | None = None
    zone_type: str | None = None
    polygon_points: list[PolygonPoint] | None = None
    color: str | None = None
    is_active: bool | None = None


class ZoneResponse(BaseModel):
    id: UUID
    camera_id: UUID
    name: str
    zone_type: str
    polygon_points: list[dict]
    color: str
    is_active: bool

    model_config = {"from_attributes": True}

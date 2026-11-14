import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, new_uuid


class Camera(Base, TimestampMixin):
    __tablename__ = "cameras"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    restaurant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("restaurants.id"))
    name: Mapped[str] = mapped_column(String(255))
    location_description: Mapped[str | None] = mapped_column(String(500))
    rtsp_url: Mapped[str | None] = mapped_column(String(500))
    stream_type: Mapped[str] = mapped_column(String(20), default="rtsp")
    resolution_w: Mapped[int | None] = mapped_column(Integer)
    resolution_h: Mapped[int | None] = mapped_column(Integer)
    fps: Mapped[int] = mapped_column(Integer, default=15)
    status: Mapped[str] = mapped_column(String(20), default="offline")
    last_heartbeat: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    restaurant = relationship("Restaurant", back_populates="cameras")
    zones = relationship("Zone", back_populates="camera", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="camera")

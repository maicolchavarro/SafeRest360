import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, new_uuid


class Alert(Base, TimestampMixin):
    __tablename__ = "alerts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    rule_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("rules.id"))
    camera_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cameras.id"))
    zone_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("zones.id"))
    restaurant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("restaurants.id"))
    alert_type: Mapped[str] = mapped_column(String(50))
    severity: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default="new")
    description: Mapped[str | None] = mapped_column(Text)
    snapshot_path: Mapped[str | None] = mapped_column(String(500))
    detection_data: Mapped[dict | None] = mapped_column(JSON)
    triggered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolved_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))

    rule = relationship("Rule", back_populates="alerts")
    camera = relationship("Camera", back_populates="alerts")
    zone = relationship("Zone", back_populates="alerts")
    restaurant = relationship("Restaurant", back_populates="alerts")
    notifications = relationship("Notification", back_populates="alert", cascade="all, delete-orphan")

    @property
    def has_snapshot(self) -> bool:
        return bool(self.snapshot_path)

import uuid

from sqlalchemy import JSON, Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, new_uuid


class Zone(Base, TimestampMixin):
    __tablename__ = "zones"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    camera_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cameras.id"))
    name: Mapped[str] = mapped_column(String(255))
    zone_type: Mapped[str] = mapped_column(String(30))
    polygon_points: Mapped[list] = mapped_column(JSON)
    color: Mapped[str] = mapped_column(String(7), default="#FF0000")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    camera = relationship("Camera", back_populates="zones")
    rules = relationship("Rule", back_populates="zone", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="zone")

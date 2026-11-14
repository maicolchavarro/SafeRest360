import uuid

from sqlalchemy import JSON, Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, new_uuid


class Rule(Base, TimestampMixin):
    __tablename__ = "rules"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    zone_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("zones.id"))
    rule_type: Mapped[str] = mapped_column(String(50))
    parameters: Mapped[dict] = mapped_column(JSON)
    schedule: Mapped[dict | None] = mapped_column(JSON)
    severity: Mapped[str] = mapped_column(String(20), default="medium")
    cooldown_seconds: Mapped[int] = mapped_column(default=300)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    zone = relationship("Zone", back_populates="rules")
    alerts = relationship("Alert", back_populates="rule")

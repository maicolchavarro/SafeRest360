import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin, new_uuid


class ModelRecord(Base, TimestampMixin):
    __tablename__ = "model_registry"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(255))
    variant: Mapped[str] = mapped_column(String(50))
    version: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default="candidate")
    file_path: Mapped[str | None] = mapped_column(String(500))
    file_size_mb: Mapped[float | None] = mapped_column(Float)
    metrics: Mapped[dict | None] = mapped_column(JSON)
    training_config: Mapped[dict | None] = mapped_column(JSON)
    dataset_info: Mapped[dict | None] = mapped_column(JSON)
    mlflow_run_id: Mapped[str | None] = mapped_column(String(100))
    license: Mapped[str | None] = mapped_column(String(50))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    promoted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

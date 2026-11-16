from pydantic_settings import BaseSettings
from pydantic import Field
from pathlib import Path
from typing import Literal


class Settings(BaseSettings):
    PROJECT_NAME: str = "SafeRest360"
    API_V1_PREFIX: str = "/api/v1"

    SECRET_KEY: str = "change-me-to-a-random-string"
    DATABASE_URL: str = "sqlite+aiosqlite:///./saferest360.db"
    CORS_ORIGINS: str = "http://localhost:3000"

    JWT_SECRET_KEY: str = "change-me-jwt-secret"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    REDIS_URL: str | None = None

    # Messaging: telegram (default), whatsapp (legacy/desactivado), disabled
    NOTIFICATION_CHANNEL: Literal["telegram", "whatsapp", "disabled"] = "telegram"
    TELEGRAM_BOT_TOKEN: str | None = None
    TELEGRAM_TEST_MODE: bool = False

    # WhatsApp legacy client (inactivo por defecto; Telegram es el canal principal)
    WHATSAPP_PHONE_NUMBER_ID: str | None = None
    WHATSAPP_ACCESS_TOKEN: str | None = None
    WHATSAPP_VERIFY_TOKEN: str | None = None
    WHATSAPP_TEST_MODE: bool = True

    # Alertas y retención de snapshots (en días)
    ALERT_RETENTION_DAYS: int = Field(default=30, ge=1, le=365)

    # Ultralytics resolves (and downloads once) a bare model name; see Brief section H for the choice
    VISION_MODEL_PATH: str = "yolov8n.pt"
    VISION_CONFIDENCE_THRESHOLD: float = 0.5
    VISION_DEVICE: str = "cpu"

    STREAM_WORKERS_ENABLED: bool = True
    STREAM_ANALYSIS_FPS: float = 5.0
    STREAM_SYNC_SECONDS: float = 10.0

    MLFLOW_TRACKING_URI: str = "sqlite:///./mlflow.db"

    SNAPSHOT_STORAGE: str = "local"
    SNAPSHOT_LOCAL_PATH: str = "./snapshots"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",")]

    model_config = {
        "env_file": (Path(__file__).resolve().parents[2] / ".env", Path(__file__).resolve().parents[1] / ".env"),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()

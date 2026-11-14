from pydantic_settings import BaseSettings
from pathlib import Path


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

    WHATSAPP_PHONE_NUMBER_ID: str | None = None
    WHATSAPP_ACCESS_TOKEN: str | None = None
    WHATSAPP_VERIFY_TOKEN: str | None = None
    WHATSAPP_TEST_MODE: bool = True

    VISION_MODEL_PATH: str = "vision-engine/models/yolov8n.pt"
    VISION_CONFIDENCE_THRESHOLD: float = 0.5
    VISION_DEVICE: str = "cpu"

    MLFLOW_TRACKING_URI: str = "sqlite:///./mlflow.db"

    SNAPSHOT_STORAGE: str = "local"
    SNAPSHOT_LOCAL_PATH: str = "./snapshots"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",")]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()

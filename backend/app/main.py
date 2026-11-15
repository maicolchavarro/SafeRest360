import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.config import settings
from app.database import async_session, create_tables
from app.services.rule_defaults import ensure_default_rules
from app.services.stream_manager import stream_manager

_app_logger = logging.getLogger("saferest360")
if not _app_logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    _app_logger.addHandler(_handler)
    _app_logger.setLevel(logging.INFO)


class _SkipLivePolling(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return "/live" not in record.getMessage()


logging.getLogger("uvicorn.access").addFilter(_SkipLivePolling())


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_tables()
    await _seed_admin_if_empty()
    async with async_session() as db:
        await ensure_default_rules(db)
    if settings.STREAM_WORKERS_ENABLED:
        await stream_manager.start()
    yield
    await stream_manager.stop()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "SafeRest360 API"}


async def _seed_admin_if_empty():
    """Create default restaurant and admin user on first run."""
    from sqlalchemy import select

    from app.core.security import hash_password
    from app.database import async_session
    from app.models.restaurant import Restaurant
    from app.models.user import User

    async with async_session() as db:
        result = await db.execute(select(User).limit(1))
        if result.scalar_one_or_none() is not None:
            return

        restaurant = Restaurant(name="Restaurante Demo", address="Tunja, Boyacá")
        db.add(restaurant)
        await db.flush()

        admin = User(
            restaurant_id=restaurant.id,
            email="admin@saferest360.com",
            hashed_password=hash_password("admin123"),
            full_name="Administrador",
            role="admin",
        )
        db.add(admin)
        await db.commit()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

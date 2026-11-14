from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.config import settings
from app.database import create_tables


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_tables()
    await _seed_admin_if_empty()
    yield


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

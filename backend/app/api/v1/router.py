from fastapi import APIRouter

from app.api.v1 import alerts, notifications, auth, cameras, inference, rules, users, zones

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(cameras.router)
api_router.include_router(zones.router)
api_router.include_router(rules.router)
api_router.include_router(alerts.router)
api_router.include_router(inference.router)

api_router.include_router(notifications.router)

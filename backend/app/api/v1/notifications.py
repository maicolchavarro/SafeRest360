from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_admin
from app.config import settings
from app.database import get_db
from app.models import Alert, Notification, User

router = APIRouter(tags=["notifications"])


@router.get("/notifications/config")
async def notification_config(admin: User = Depends(require_admin)):
    channel = settings.NOTIFICATION_CHANNEL
    if channel == "disabled":
        return {"channel": channel, "test_mode": True, "credentials_configured": False, "recipient_configured": False}
    telegram = channel == "telegram"
    return {
        "channel": channel,
        "test_mode": settings.TELEGRAM_TEST_MODE if telegram else settings.WHATSAPP_TEST_MODE,
        "credentials_configured": bool(settings.TELEGRAM_BOT_TOKEN) if telegram else bool(
            settings.WHATSAPP_ACCESS_TOKEN and settings.WHATSAPP_PHONE_NUMBER_ID
        ),
        "recipient_configured": bool(admin.telegram_chat_id) if telegram else bool(admin.phone_whatsapp),
    }


class NotificationResponse(BaseModel):
    id: UUID
    channel: str
    status: str
    error_message: str | None
    model_config = {"from_attributes": True}


@router.get("/alerts/{alert_id}/notifications", response_model=list[NotificationResponse])
async def alert_notifications(
    alert_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    alert = await db.scalar(select(Alert).where(
        Alert.id == alert_id, Alert.restaurant_id == user.restaurant_id
    ))
    if alert is None:
        raise HTTPException(status_code=404, detail="Alerta no encontrada")
    result = await db.scalars(select(Notification).where(Notification.alert_id == alert_id))
    return result.all()

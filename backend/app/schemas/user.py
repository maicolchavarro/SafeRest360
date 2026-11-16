from uuid import UUID

from pydantic import BaseModel, EmailStr, field_validator
from app.services.telegram_client import normalize_chat_id, TelegramDeliveryError


class TelegramRecipient(BaseModel):
    telegram_chat_id: str | None = None

    @field_validator("telegram_chat_id")
    @classmethod
    def validate_telegram_chat_id(cls, value):
        if value is None or not value.strip():
            return None
        try:
            return normalize_chat_id(value)
        except TelegramDeliveryError as exc:
            raise ValueError(str(exc)) from None


class UserCreate(TelegramRecipient):
    email: EmailStr
    password: str
    full_name: str | None = None
    role: str = "operator"
    phone_whatsapp: str | None = None


class UserUpdate(TelegramRecipient):
    email: EmailStr | None = None
    full_name: str | None = None
    role: str | None = None
    phone_whatsapp: str | None = None
    is_active: bool | None = None


class UserResponse(BaseModel):
    id: UUID
    restaurant_id: UUID
    email: str
    full_name: str | None
    role: str
    phone_whatsapp: str | None
    is_active: bool
    telegram_chat_id: str | None

    model_config = {"from_attributes": True}

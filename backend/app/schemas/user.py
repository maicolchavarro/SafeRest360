from uuid import UUID

from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None
    role: str = "operator"
    phone_whatsapp: str | None = None


class UserUpdate(BaseModel):
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

    model_config = {"from_attributes": True}

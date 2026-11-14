from uuid import UUID

from pydantic import BaseModel


class RuleCreate(BaseModel):
    rule_type: str
    parameters: dict
    schedule: dict | None = None
    severity: str = "medium"
    cooldown_seconds: int = 300


class RuleUpdate(BaseModel):
    rule_type: str | None = None
    parameters: dict | None = None
    schedule: dict | None = None
    severity: str | None = None
    cooldown_seconds: int | None = None
    is_active: bool | None = None


class RuleResponse(BaseModel):
    id: UUID
    zone_id: UUID
    rule_type: str
    parameters: dict
    schedule: dict | None
    severity: str
    cooldown_seconds: int
    is_active: bool

    model_config = {"from_attributes": True}

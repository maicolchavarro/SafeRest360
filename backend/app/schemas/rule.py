import re
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

RuleType = Literal["no_entry", "zone_abandoned", "max_occupancy"]
Severity = Literal["low", "medium", "high", "critical"]

# rule_type -> {parameter: (min, max, default)}
PARAMETER_SPECS: dict[str, dict[str, tuple[int, int, int]]] = {
    "no_entry": {"confirm_seconds": (0, 600, 2)},
    "zone_abandoned": {"timeout_seconds": (10, 86_400, 120)},
    "max_occupancy": {"max_persons": (1, 100, 5), "confirm_seconds": (0, 600, 2)},
}

_HHMM = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


def normalize_parameters(rule_type: str, parameters: dict | None) -> dict:
    """Keep only the parameters this rule type uses, fill defaults and check ranges."""
    specs = PARAMETER_SPECS.get(rule_type)
    if specs is None:
        raise ValueError(f"Tipo de regla no soportado: {rule_type}")
    parameters = parameters or {}
    result = {}
    for name, (low, high, default) in specs.items():
        value = parameters.get(name, default)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not low <= value <= high:
            raise ValueError(f"{name} debe estar entre {low} y {high}")
        result[name] = int(value)
    return result


class RuleSchedule(BaseModel):
    """Weekly window in the restaurant's timezone. 0 = Monday. end <= start means it runs past midnight."""

    days: list[int] = Field(min_length=1)
    start: str
    end: str

    @field_validator("days")
    @classmethod
    def _days(cls, days: list[int]) -> list[int]:
        if any(d < 0 or d > 6 for d in days):
            raise ValueError("Los días van de 0 (lunes) a 6 (domingo)")
        return sorted(set(days))

    @field_validator("start", "end")
    @classmethod
    def _hhmm(cls, value: str) -> str:
        if not _HHMM.match(value):
            raise ValueError("La hora debe tener formato HH:MM")
        return value


class RuleCreate(BaseModel):
    rule_type: RuleType
    parameters: dict = Field(default_factory=dict)
    schedule: RuleSchedule | None = None
    severity: Severity = "medium"
    cooldown_seconds: int = Field(300, ge=0, le=86_400)

    @model_validator(mode="after")
    def _params(self):
        self.parameters = normalize_parameters(self.rule_type, self.parameters)
        return self


class RuleUpdate(BaseModel):
    rule_type: RuleType | None = None
    parameters: dict | None = None
    schedule: RuleSchedule | None = None
    severity: Severity | None = None
    cooldown_seconds: int | None = Field(None, ge=0, le=86_400)
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

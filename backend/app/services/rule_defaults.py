from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rule import Rule
from app.models.zone import Zone

# zone_type -> (rule_type, parameters, severity, cooldown_seconds)
DEFAULT_RULES = {
    "restricted": ("no_entry", {}, "high", 120),
    "monitored": ("zone_abandoned", {"timeout_seconds": 120}, "medium", 300),
    "required_presence": ("zone_abandoned", {"timeout_seconds": 120}, "medium", 300),
}


def default_rule_for(zone: Zone) -> Rule | None:
    spec = DEFAULT_RULES.get(zone.zone_type)
    if spec is None:
        return None
    rule_type, parameters, severity, cooldown = spec
    return Rule(
        zone_id=zone.id,
        rule_type=rule_type,
        parameters=dict(parameters),
        severity=severity,
        cooldown_seconds=cooldown,
    )


async def ensure_default_rules(db: AsyncSession) -> int:
    """Give every active zone without rules its default rule (zones created before rules existed)."""
    has_rule = select(Rule.zone_id)
    zones = (
        await db.execute(select(Zone).where(Zone.is_active == True, Zone.id.not_in(has_rule)))
    ).scalars().all()
    created = 0
    for zone in zones:
        rule = default_rule_for(zone)
        if rule is not None:
            db.add(rule)
            created += 1
    await db.commit()
    return created

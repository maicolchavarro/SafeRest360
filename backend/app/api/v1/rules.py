from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.api.v1.zones import get_owned_zone
from app.database import get_db
from app.models.alert import Alert
from app.models.camera import Camera
from app.models.rule import Rule
from app.models.user import User
from app.models.zone import Zone
from app.schemas.rule import RuleCreate, RuleResponse, RuleUpdate, normalize_parameters

router = APIRouter(tags=["rules"])


async def _get_owned_rule(rule_id: UUID, user: User, db: AsyncSession) -> Rule:
    result = await db.execute(
        select(Rule)
        .join(Zone, Rule.zone_id == Zone.id)
        .join(Camera, Zone.camera_id == Camera.id)
        .where(Rule.id == rule_id, Camera.restaurant_id == user.restaurant_id)
    )
    rule = result.scalar_one_or_none()
    if rule is None:
        raise HTTPException(status_code=404, detail="Regla no encontrada")
    return rule


@router.get("/zones/{zone_id}/rules", response_model=list[RuleResponse])
async def list_rules(
    zone_id: UUID,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    await get_owned_zone(zone_id, user, db)
    # paused rules (is_active = False) are listed too so they can be resumed
    result = await db.execute(select(Rule).where(Rule.zone_id == zone_id).order_by(Rule.created_at))
    return result.scalars().all()


@router.post("/zones/{zone_id}/rules", response_model=RuleResponse, status_code=status.HTTP_201_CREATED)
async def create_rule(
    zone_id: UUID,
    body: RuleCreate,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    await get_owned_zone(zone_id, user, db)
    rule = Rule(zone_id=zone_id, **body.model_dump())
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return rule


@router.patch("/rules/{rule_id}", response_model=RuleResponse)
async def update_rule(
    rule_id: UUID,
    body: RuleUpdate,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    rule = await _get_owned_rule(rule_id, user, db)
    updates = body.model_dump(exclude_unset=True)
    if "rule_type" in updates or "parameters" in updates:
        rule_type = updates.get("rule_type") or rule.rule_type
        parameters = updates["parameters"] if "parameters" in updates else rule.parameters
        try:
            updates["parameters"] = normalize_parameters(rule_type, parameters)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc))
    for field, value in updates.items():
        setattr(rule, field, value)
    await db.commit()
    await db.refresh(rule)
    return rule


@router.delete("/rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rule(
    rule_id: UUID,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    rule = await _get_owned_rule(rule_id, user, db)
    has_alerts = (await db.execute(select(Alert.id).where(Alert.rule_id == rule.id).limit(1))).first()
    if has_alerts:
        raise HTTPException(
            status_code=409,
            detail="La regla tiene alertas registradas; páusala para conservar el historial",
        )
    await db.delete(rule)
    await db.commit()

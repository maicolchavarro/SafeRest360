import os
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest

_db_dir = tempfile.mkdtemp(prefix="saferest360-test-")
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{Path(_db_dir) / 'test.db'}"

from fastapi.testclient import TestClient  # noqa: E402

from app.core.security import hash_password  # noqa: E402
from app.database import async_session  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Alert, Restaurant, Rule, User  # noqa: E402

PASSWORD = "test-password-123"


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


def _run(client, coro_fn, *args):
    return client.portal.call(coro_fn, *args)


async def _create_tenant(suffix: str) -> dict:
    async with async_session() as db:
        restaurant = Restaurant(name=f"Restaurante {suffix}")
        db.add(restaurant)
        await db.flush()
        users = {}
        for role in ("admin", "operator"):
            u = User(
                restaurant_id=restaurant.id,
                email=f"{role}-{suffix}@saferest360.com",
                hashed_password=hash_password(PASSWORD),
                role=role,
            )
            db.add(u)
            users[role] = u
        await db.commit()
        return {
            "restaurant_id": restaurant.id,
            "admin_email": users["admin"].email,
            "operator_email": users["operator"].email,
        }


def _login(client, email: str) -> dict:
    r = client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def make_tenant(client):
    """Create an isolated restaurant with an admin and an operator; return auth headers."""

    def factory():
        info = _run(client, _create_tenant, uuid.uuid4().hex[:8])
        info["admin"] = _login(client, info["admin_email"])
        info["operator"] = _login(client, info["operator_email"])
        return info

    return factory


@pytest.fixture
def tenant(make_tenant):
    return make_tenant()


ZONE_BODY = {
    "name": "Bodega",
    "zone_type": "restricted",
    "polygon_points": [{"x": 0.1, "y": 0.1}, {"x": 0.5, "y": 0.1}, {"x": 0.5, "y": 0.5}],
}


@pytest.fixture
def camera_with_zone(client, tenant):
    cam = client.post("/api/v1/cameras", json={"name": "Cocina"}, headers=tenant["admin"]).json()
    zone = client.post(
        f"/api/v1/cameras/{cam['id']}/zones", json=ZONE_BODY, headers=tenant["admin"]
    ).json()
    return cam, zone


async def _create_alert(restaurant_id, camera_id, zone_id) -> uuid.UUID:
    async with async_session() as db:
        rule = Rule(zone_id=zone_id, rule_type="no_entry", parameters={})
        db.add(rule)
        await db.flush()
        alert = Alert(
            rule_id=rule.id,
            camera_id=camera_id,
            zone_id=zone_id,
            restaurant_id=restaurant_id,
            alert_type="no_entry",
            severity="high",
            triggered_at=datetime.now(timezone.utc),
        )
        db.add(alert)
        await db.commit()
        return alert.id


@pytest.fixture
def make_alert(client):
    def factory(restaurant_id, camera_id, zone_id):
        return str(
            _run(client, _create_alert, restaurant_id, uuid.UUID(camera_id), uuid.UUID(zone_id))
        )

    return factory

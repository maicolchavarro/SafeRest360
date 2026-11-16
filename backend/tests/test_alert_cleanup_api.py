import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import select

from app.config import settings
from app.database import async_session
from app.models import Alert, Notification, User


async def prepare(alert_id, age=0):
    async with async_session() as db:
        alert = await db.get(Alert, uuid.UUID(alert_id))
        alert.triggered_at = datetime.now(timezone.utc) - timedelta(days=age)
        path = Path(settings.SNAPSHOT_LOCAL_PATH) / str(alert.restaurant_id) / f"{alert.id}.jpg"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"snapshot")
        alert.snapshot_path = str(path)
        admin = await db.scalar(select(User).where(User.restaurant_id == alert.restaurant_id, User.role == "admin"))
        db.add(Notification(alert_id=alert.id, user_id=admin.id, channel="telegram", status="test"))
        await db.commit()
        return path


async def notification_count(alert_id):
    async with async_session() as db:
        return len((await db.scalars(select(Notification).where(Notification.alert_id == uuid.UUID(alert_id)))).all())


def test_delete_requires_own_admin_and_removes_notifications(client, tenant, make_tenant, camera_with_zone, make_alert):
    cam, zone = camera_with_zone
    aid = make_alert(tenant["restaurant_id"], cam["id"], zone["id"])
    path = client.portal.call(prepare, aid)
    other = make_tenant()
    url = f"/api/v1/alerts/{aid}"
    assert client.delete(url, headers=tenant["operator"]).status_code == 403
    assert client.delete(url, headers=other["admin"]).status_code == 404
    assert path.exists()
    response = client.delete(url, headers=tenant["admin"])
    assert response.status_code == 200
    assert response.json()["file_deleted"] is True
    assert not path.exists()
    assert client.portal.call(notification_count, aid) == 0
    assert client.get(url, headers=tenant["admin"]).status_code == 404


def test_cleanup_only_old_records_and_checks_days(client, tenant, camera_with_zone, make_alert):
    cam, zone = camera_with_zone
    old = make_alert(tenant["restaurant_id"], cam["id"], zone["id"])
    recent = make_alert(tenant["restaurant_id"], cam["id"], zone["id"])
    old_path = client.portal.call(prepare, old, 40)
    recent_path = client.portal.call(prepare, recent, 1)
    endpoint = "/api/v1/alerts/cleanup"
    assert client.post(endpoint, headers=tenant["operator"]).status_code == 403
    for invalid in ("0", "-1", "366", "1.5"):
        assert client.post(endpoint + "?older_than_days=" + invalid, headers=tenant["admin"]).status_code == 422
    response = client.post(endpoint + "?older_than_days=30", headers=tenant["admin"])
    assert response.status_code == 200
    assert response.json()["alerts_deleted"] == 1
    assert response.json()["files_deleted"] == 1
    assert response.json()["alerts_skipped"] == 0
    assert not old_path.exists() and recent_path.exists()
    assert client.portal.call(notification_count, old) == 0
    assert client.get(f"/api/v1/alerts/{recent}", headers=tenant["admin"]).status_code == 200


def test_cleanup_keeps_records_when_file_deletion_fails(client, tenant, camera_with_zone, make_alert, monkeypatch):
    cam, zone = camera_with_zone
    aid = make_alert(tenant["restaurant_id"], cam["id"], zone["id"])
    path = client.portal.call(prepare, aid, 40)
    original = Path.unlink
    def fail_one(self, *args, **kwargs):
        if self == path:
            raise PermissionError("test")
        return original(self, *args, **kwargs)
    monkeypatch.setattr(Path, "unlink", fail_one)
    response = client.post("/api/v1/alerts/cleanup?older_than_days=30", headers=tenant["admin"])
    assert response.status_code == 200
    assert response.json()["alerts_deleted"] == 0
    assert response.json()["alerts_skipped"] == 1
    assert path.exists()
    assert client.get(f"/api/v1/alerts/{aid}", headers=tenant["admin"]).status_code == 200

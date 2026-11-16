import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select

from app.config import settings
from app.database import async_session
from app.models import Notification
from app.services.stream_manager import PendingAlert, stream_manager
from app.services.telegram_client import TelegramDeliveryError


@pytest.fixture(autouse=True)
def telegram_mode(monkeypatch):
    monkeypatch.setattr(settings, "NOTIFICATION_CHANNEL", "telegram")
    monkeypatch.setattr(settings, "TELEGRAM_TEST_MODE", True)


def configure_admin(client, tenant, chat_id="123456"):
    me = client.get("/api/v1/auth/me", headers=tenant["admin"]).json()
    response = client.patch(
        f"/api/v1/users/{me['id']}", headers=tenant["admin"],
        json={"telegram_chat_id": chat_id},
    )
    assert response.status_code == 200, response.text
    return me


def pending_alert(client, tenant, camera_with_zone):
    cam, zone = camera_with_zone
    rule = client.get(f"/api/v1/zones/{zone['id']}/rules", headers=tenant["admin"]).json()[0]
    return PendingAlert(
        camera_id=uuid.UUID(cam["id"]), rule_id=uuid.UUID(rule["id"]), zone_id=uuid.UUID(zone["id"]),
        event={"event_type": "no_entry", "severity": "high", "persons_detected": 1,
               "description": "Persona en zona restringida", "detection_data": [],
               "timestamp": datetime.now(timezone.utc).isoformat()},
        snapshot_jpeg=b"test-snapshot",
    )


async def rows(alert_id):
    async with async_session() as db:
        result = await db.scalars(select(Notification).where(Notification.alert_id == alert_id))
        return [(r.channel, r.status, r.sent_at, r.delivered_at) for r in result]


def test_dry_run_records_without_delivery_timestamp(client, tenant, camera_with_zone, monkeypatch):
    configure_admin(client, tenant)
    sender = AsyncMock(return_value={"status": "test", "message_id": None})
    monkeypatch.setattr("app.services.stream_manager.send_telegram", sender)
    alert = client.portal.call(stream_manager.persist_alert, pending_alert(client, tenant, camera_with_zone))
    assert client.portal.call(rows, alert.id) == [("telegram", "test", None, None)]
    sender.assert_awaited_once()
    assert sender.call_args.args[0] == "123456"


def test_provider_failure_keeps_alert_and_snapshot(client, tenant, camera_with_zone, monkeypatch):
    configure_admin(client, tenant)
    sender = AsyncMock(side_effect=TelegramDeliveryError("Timeout", "unknown"))
    monkeypatch.setattr("app.services.stream_manager.send_telegram", sender)
    alert = client.portal.call(stream_manager.persist_alert, pending_alert(client, tenant, camera_with_zone))
    assert client.get(f"/api/v1/alerts/{alert.id}", headers=tenant["admin"]).status_code == 200
    assert client.get(f"/api/v1/alerts/{alert.id}/snapshot", headers=tenant["admin"]).status_code == 200
    assert client.portal.call(rows, alert.id) == [("telegram", "unknown", None, None)]


def test_notification_history_is_tenant_scoped(client, tenant, make_tenant, camera_with_zone):
    configure_admin(client, tenant)
    alert = client.portal.call(stream_manager.persist_alert, pending_alert(client, tenant, camera_with_zone))
    other = make_tenant()
    path = f"/api/v1/alerts/{alert.id}/notifications"
    assert client.get(path, headers=tenant["operator"]).json()[0]["channel"] == "telegram"
    assert client.get(path, headers=other["admin"]).status_code == 404
    assert client.get(path).status_code in (401, 403)


def test_recipient_validation_and_removal(client, tenant):
    me = configure_admin(client, tenant)
    path = f"/api/v1/users/{me['id']}"
    assert client.patch(path, headers=tenant["admin"], json={"telegram_chat_id": "abc"}).status_code == 422
    assert client.patch(path, headers=tenant["admin"], json={"telegram_chat_id": None}).json()["telegram_chat_id"] is None
    assert client.patch(path, headers=tenant["operator"], json={"telegram_chat_id": "123"}).status_code == 403


def test_disabled_channel_never_sends(client, tenant, camera_with_zone, monkeypatch):
    configure_admin(client, tenant)
    monkeypatch.setattr(settings, "NOTIFICATION_CHANNEL", "disabled")
    sender = AsyncMock()
    monkeypatch.setattr("app.services.stream_manager.send_telegram", sender)
    alert = client.portal.call(stream_manager.persist_alert, pending_alert(client, tenant, camera_with_zone))
    assert client.portal.call(rows, alert.id) == []
    sender.assert_not_awaited()


def test_config_has_no_bot_token(client, tenant, monkeypatch):
    monkeypatch.setattr(settings, "TELEGRAM_BOT_TOKEN", "123:SECRET")
    response = client.get("/api/v1/notifications/config", headers=tenant["admin"])
    assert response.status_code == 200
    assert response.json()["channel"] == "telegram"
    assert response.json()["credentials_configured"] is True
    assert "SECRET" not in response.text
    assert client.get("/api/v1/notifications/config", headers=tenant["operator"]).status_code == 403


def test_only_current_restaurant_admins_and_one_copy_per_chat(
    client, tenant, make_tenant, camera_with_zone, monkeypatch
):
    configure_admin(client, tenant)
    other = make_tenant()
    configure_admin(client, other, "999999")
    for role in ("admin", "operator"):
        response = client.post("/api/v1/users", headers=tenant["admin"], json={
            "email": f"{role}-{uuid.uuid4().hex}@example.com", "password": "test-password-123",
            "role": role, "telegram_chat_id": "123456" if role == "admin" else "888888",
        })
        assert response.status_code == 201
    sender = AsyncMock(return_value={"status": "sent", "message_id": "123456:42"})
    monkeypatch.setattr("app.services.stream_manager.send_telegram", sender)
    alert = client.portal.call(stream_manager.persist_alert, pending_alert(client, tenant, camera_with_zone))
    sender.assert_awaited_once()
    assert sender.call_args.args[0] == "123456"
    notifications = client.portal.call(rows, alert.id)
    assert len(notifications) == 1
    assert notifications[0][1] == "sent" and notifications[0][2] is not None
    assert notifications[0][3] is None

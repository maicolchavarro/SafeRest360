import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import cv2
import pytest

from app.services.stream_manager import CameraWorker, PendingAlert, stream_manager
from tests.conftest import ZONE_BODY

BUS = Path(__file__).resolve().parents[2] / "vision-engine" / "bus.jpg"


def _rules(client, headers, zone_id):
    return client.get(f"/api/v1/zones/{zone_id}/rules", headers=headers).json()


def test_new_zone_gets_its_default_rule(client, tenant, camera_with_zone):
    _, zone = camera_with_zone
    rules = _rules(client, tenant["admin"], zone["id"])
    assert [(r["rule_type"], r["severity"]) for r in rules] == [("no_entry", "high")]


def test_monitored_zone_default_rule_is_zone_abandoned(client, tenant):
    cam = client.post("/api/v1/cameras", json={"name": "Caja"}, headers=tenant["admin"]).json()
    zone = client.post(
        f"/api/v1/cameras/{cam['id']}/zones",
        json={**ZONE_BODY, "zone_type": "monitored"},
        headers=tenant["admin"],
    ).json()
    rules = _rules(client, tenant["admin"], zone["id"])
    assert rules[0]["rule_type"] == "zone_abandoned"
    assert rules[0]["parameters"] == {"timeout_seconds": 120}


@pytest.mark.parametrize("url", ["file:///C:/Windows/win.ini", "C:\\secreto.mp4", "http://x/y", "rtsp://"])
def test_stream_url_must_be_rtsp(client, tenant, url):
    r = client.post("/api/v1/cameras", json={"name": "X", "rtsp_url": url}, headers=tenant["admin"])
    assert r.status_code == 422


def test_camera_reports_whether_it_has_a_stream_url(client, tenant):
    cam = client.post(
        "/api/v1/cameras",
        json={"name": "Cocina", "rtsp_url": "rtsp://user:pass@127.0.0.1:8554/cocina"},
        headers=tenant["admin"],
    ).json()
    assert cam["has_stream_url"] is True
    assert "rtsp_url" not in cam


class _FakeWorker:
    latest_jpeg = b"\xff\xd8fake-jpeg\xff\xd9"
    status = "online"
    persons_in_view = 2
    analysis_fps = 4.8
    last_frame_at = datetime.now(timezone.utc)
    error = None


def test_live_frame_and_status_are_tenant_scoped(client, make_tenant, monkeypatch):
    a, b = make_tenant(), make_tenant()
    cam = client.post("/api/v1/cameras", json={"name": "Cocina"}, headers=a["admin"]).json()
    monkeypatch.setitem(stream_manager._workers, uuid.UUID(cam["id"]), _FakeWorker())

    r = client.get(f"/api/v1/cameras/{cam['id']}/live.jpg", headers=a["operator"])
    assert r.status_code == 200 and r.headers["content-type"] == "image/jpeg"
    assert r.content == _FakeWorker.latest_jpeg

    status = client.get(f"/api/v1/cameras/{cam['id']}/live/status", headers=a["operator"]).json()
    assert status["streaming"] is True and status["persons_in_view"] == 2

    assert client.get(f"/api/v1/cameras/{cam['id']}/live.jpg", headers=b["admin"]).status_code == 404
    assert client.get(f"/api/v1/cameras/{cam['id']}/live/status", headers=b["admin"]).status_code == 404


def test_live_frame_404_when_camera_not_streaming(client, tenant):
    cam = client.post("/api/v1/cameras", json={"name": "Sin stream"}, headers=tenant["admin"]).json()
    assert client.get(f"/api/v1/cameras/{cam['id']}/live.jpg", headers=tenant["admin"]).status_code == 404
    status = client.get(f"/api/v1/cameras/{cam['id']}/live/status", headers=tenant["admin"]).json()
    assert status["streaming"] is False and status["error"]


def test_event_becomes_alert_with_snapshot_and_whatsapp_log(client, make_tenant, camera_with_zone, tenant):
    cam, zone = camera_with_zone
    me = client.get("/api/v1/auth/me", headers=tenant["admin"]).json()
    client.patch(f"/api/v1/users/{me['id']}", json={"phone_whatsapp": "+573000000000"}, headers=tenant["admin"])
    rule = _rules(client, tenant["admin"], zone["id"])[0]

    pending = PendingAlert(
        camera_id=uuid.UUID(cam["id"]),
        rule_id=uuid.UUID(rule["id"]),
        zone_id=uuid.UUID(zone["id"]),
        event={
            "event_type": "no_entry", "severity": "high", "persons_detected": 1,
            "description": "Persona detectada en zona restringida: Bodega",
            "detection_data": [{"bbox": [1, 2, 3, 4], "confidence": 0.9}],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        snapshot_jpeg=b"\xff\xd8snapshot\xff\xd9",
    )
    alert = client.portal.call(stream_manager.persist_alert, pending)

    listed = client.get("/api/v1/alerts", headers=tenant["operator"]).json()
    assert [a["id"] for a in listed] == [str(alert.id)]
    assert listed[0]["has_snapshot"] is True and "snapshot_path" not in listed[0]
    assert listed[0]["detection_data"]["persons_detected"] == 1

    img = client.get(f"/api/v1/alerts/{alert.id}/snapshot", headers=tenant["operator"])
    assert img.status_code == 200 and img.content == pending.snapshot_jpeg

    other = make_tenant()
    assert client.get(f"/api/v1/alerts/{alert.id}/snapshot", headers=other["admin"]).status_code == 404


@pytest.mark.skipif(not BUS.exists(), reason="vision-engine/bus.jpg not available")
def test_worker_reads_stream_detects_people_and_fires_rule(tmp_path):
    frame = cv2.imread(str(BUS))
    video = tmp_path / "cam.mp4"
    writer = cv2.VideoWriter(str(video), cv2.VideoWriter_fourcc(*"mp4v"), 10, (frame.shape[1], frame.shape[0]))
    for _ in range(30):
        writer.write(frame)
    writer.release()

    events = []
    worker = CameraWorker(uuid.uuid4(), str(video), analysis_fps=5, on_event=events.append)
    zone_id, rule_id = str(uuid.uuid4()), str(uuid.uuid4())
    worker.set_rules(
        [{"id": zone_id, "name": "Todo", "zone_type": "restricted", "color": "#ff0000",
          "polygon_points": [{"x": 0, "y": 0}, {"x": 1, "y": 0}, {"x": 1, "y": 1}, {"x": 0, "y": 1}]}],
        [{"id": rule_id, "zone_id": zone_id, "rule_type": "no_entry", "parameters": {},
          "severity": "high", "cooldown_seconds": 300}],
    )
    worker.start()
    try:
        deadline = time.time() + 90
        while time.time() < deadline and not (events and worker.latest_jpeg):
            time.sleep(0.2)
    finally:
        worker.stop()

    assert worker.latest_jpeg and worker.latest_jpeg[:2] == b"\xff\xd8"
    assert worker.persons_in_view >= 3
    assert len(events) == 1, "cooldown must keep one alert per rule"
    assert str(events[0].rule_id) == rule_id and events[0].event["persons_detected"] >= 3
    assert events[0].snapshot_jpeg[:2] == b"\xff\xd8"

def test_alert_lifecycle(client, tenant, camera_with_zone, make_alert):
    cam, zone = camera_with_zone
    alert_id = make_alert(tenant["restaurant_id"], cam["id"], zone["id"])

    alert = client.get(f"/api/v1/alerts/{alert_id}", headers=tenant["operator"]).json()
    assert alert["status"] == "new"
    # browsers would read a timestamp without offset as local time
    assert alert["triggered_at"].endswith(("Z", "+00:00"))

    r = client.patch(
        f"/api/v1/alerts/{alert_id}", json={"status": "acknowledged"}, headers=tenant["operator"]
    )
    assert r.json()["status"] == "acknowledged"
    assert r.json()["acknowledged_at"] is not None

    r = client.patch(
        f"/api/v1/alerts/{alert_id}", json={"status": "resolved"}, headers=tenant["operator"]
    )
    assert r.json()["status"] == "resolved"
    assert r.json()["resolved_at"] is not None


def test_alert_marked_as_false_alarm(client, tenant, camera_with_zone, make_alert):
    cam, zone = camera_with_zone
    alert_id = make_alert(tenant["restaurant_id"], cam["id"], zone["id"])
    r = client.patch(
        f"/api/v1/alerts/{alert_id}", json={"status": "false_alarm"}, headers=tenant["operator"]
    )
    assert r.json()["status"] == "false_alarm"


def test_alert_filters(client, tenant, camera_with_zone, make_alert):
    cam, zone = camera_with_zone
    first = make_alert(tenant["restaurant_id"], cam["id"], zone["id"])
    make_alert(tenant["restaurant_id"], cam["id"], zone["id"])
    client.patch(f"/api/v1/alerts/{first}", json={"status": "resolved"}, headers=tenant["admin"])

    new = client.get("/api/v1/alerts?status=new", headers=tenant["admin"]).json()
    resolved = client.get("/api/v1/alerts?status=resolved", headers=tenant["admin"]).json()
    assert len(new) == 1 and len(resolved) == 1
    assert resolved[0]["id"] == first


def test_alert_isolated_between_restaurants(client, make_tenant, make_alert):
    a, b = make_tenant(), make_tenant()
    cam = client.post("/api/v1/cameras", json={"name": "A"}, headers=a["admin"]).json()
    zone = client.post(
        f"/api/v1/cameras/{cam['id']}/zones",
        json={"name": "Z", "zone_type": "restricted", "polygon_points": [{"x": 0, "y": 0}]},
        headers=a["admin"],
    ).json()
    alert_id = make_alert(a["restaurant_id"], cam["id"], zone["id"])

    assert client.get("/api/v1/alerts", headers=b["admin"]).json() == []
    assert client.get(f"/api/v1/alerts/{alert_id}", headers=b["admin"]).status_code == 404
    assert (
        client.patch(
            f"/api/v1/alerts/{alert_id}", json={"status": "resolved"}, headers=b["admin"]
        ).status_code
        == 404
    )


def test_dashboard_summary_counts_only_own_restaurant(client, make_tenant, make_alert):
    a, b = make_tenant(), make_tenant()
    cam = client.post("/api/v1/cameras", json={"name": "A"}, headers=a["admin"]).json()
    zone = client.post(
        f"/api/v1/cameras/{cam['id']}/zones",
        json={"name": "Z", "zone_type": "restricted", "polygon_points": [{"x": 0, "y": 0}]},
        headers=a["admin"],
    ).json()
    make_alert(a["restaurant_id"], cam["id"], zone["id"])

    sa = client.get("/api/v1/dashboard/summary", headers=a["operator"]).json()
    assert sa == {
        "total_cameras": 1,
        "cameras_online": 0,
        "cameras_offline": 1,
        "alerts_today": 1,
        "alerts_pending": 1,
        "zones_configured": 1,
    }

    sb = client.get("/api/v1/dashboard/summary", headers=b["operator"]).json()
    assert sb["total_cameras"] == 0
    assert sb["alerts_today"] == 0
    assert sb["zones_configured"] == 0

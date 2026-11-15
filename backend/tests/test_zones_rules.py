from tests.conftest import ZONE_BODY

RULE_BODY = {"rule_type": "no_entry", "parameters": {}, "severity": "high"}


def test_zone_polygon_is_stored_normalized(client, tenant, camera_with_zone):
    cam, zone = camera_with_zone
    assert zone["polygon_points"] == ZONE_BODY["polygon_points"]
    listed = client.get(f"/api/v1/cameras/{cam['id']}/zones", headers=tenant["operator"]).json()
    assert [z["id"] for z in listed] == [zone["id"]]


def test_update_zone_polygon(client, tenant, camera_with_zone):
    _, zone = camera_with_zone
    new_points = [{"x": 0.0, "y": 0.0}, {"x": 1.0, "y": 0.0}, {"x": 1.0, "y": 1.0}]
    r = client.patch(
        f"/api/v1/zones/{zone['id']}", json={"polygon_points": new_points}, headers=tenant["admin"]
    )
    assert r.status_code == 200
    assert r.json()["polygon_points"] == new_points


def test_delete_zone_hides_it(client, tenant, camera_with_zone):
    cam, zone = camera_with_zone
    assert client.delete(f"/api/v1/zones/{zone['id']}", headers=tenant["admin"]).status_code == 204
    assert client.get(f"/api/v1/cameras/{cam['id']}/zones", headers=tenant["admin"]).json() == []


def test_operator_cannot_create_zone(client, tenant, camera_with_zone):
    cam, _ = camera_with_zone
    r = client.post(
        f"/api/v1/cameras/{cam['id']}/zones", json=ZONE_BODY, headers=tenant["operator"]
    )
    assert r.status_code == 403


def test_zone_isolated_between_restaurants(client, make_tenant):
    a, b = make_tenant(), make_tenant()
    cam = client.post("/api/v1/cameras", json={"name": "A"}, headers=a["admin"]).json()
    zone = client.post(
        f"/api/v1/cameras/{cam['id']}/zones", json=ZONE_BODY, headers=a["admin"]
    ).json()

    assert client.get(f"/api/v1/cameras/{cam['id']}/zones", headers=b["admin"]).status_code == 404
    assert (
        client.post(
            f"/api/v1/cameras/{cam['id']}/zones", json=ZONE_BODY, headers=b["admin"]
        ).status_code
        == 404
    )
    assert client.get(f"/api/v1/zones/{zone['id']}", headers=b["admin"]).status_code == 404
    assert (
        client.patch(
            f"/api/v1/zones/{zone['id']}", json={"name": "hack"}, headers=b["admin"]
        ).status_code
        == 404
    )
    assert client.delete(f"/api/v1/zones/{zone['id']}", headers=b["admin"]).status_code == 404

    still = client.get(f"/api/v1/zones/{zone['id']}", headers=a["admin"]).json()
    assert still["name"] == "Bodega" and still["is_active"] is True


def test_rule_crud(client, tenant, camera_with_zone):
    _, zone = camera_with_zone
    r = client.post(f"/api/v1/zones/{zone['id']}/rules", json=RULE_BODY, headers=tenant["admin"])
    assert r.status_code == 201
    rule = r.json()
    assert rule["cooldown_seconds"] == 300

    r = client.patch(
        f"/api/v1/rules/{rule['id']}", json={"cooldown_seconds": 60}, headers=tenant["admin"]
    )
    assert r.json()["cooldown_seconds"] == 60

    assert client.delete(f"/api/v1/rules/{rule['id']}", headers=tenant["admin"]).status_code == 204
    remaining = client.get(f"/api/v1/zones/{zone['id']}/rules", headers=tenant["admin"]).json()
    assert rule["id"] not in [r["id"] for r in remaining]


def test_rule_isolated_between_restaurants(client, make_tenant):
    a, b = make_tenant(), make_tenant()
    cam = client.post("/api/v1/cameras", json={"name": "A"}, headers=a["admin"]).json()
    zone = client.post(
        f"/api/v1/cameras/{cam['id']}/zones", json=ZONE_BODY, headers=a["admin"]
    ).json()
    rule = client.post(
        f"/api/v1/zones/{zone['id']}/rules", json=RULE_BODY, headers=a["admin"]
    ).json()

    assert client.get(f"/api/v1/zones/{zone['id']}/rules", headers=b["admin"]).status_code == 404
    assert (
        client.post(
            f"/api/v1/zones/{zone['id']}/rules", json=RULE_BODY, headers=b["admin"]
        ).status_code
        == 404
    )
    assert (
        client.patch(
            f"/api/v1/rules/{rule['id']}", json={"is_active": False}, headers=b["admin"]
        ).status_code
        == 404
    )
    assert client.delete(f"/api/v1/rules/{rule['id']}", headers=b["admin"]).status_code == 404

    rules = client.get(f"/api/v1/zones/{zone['id']}/rules", headers=a["admin"]).json()
    assert rule["id"] in [r["id"] for r in rules] and all(r["is_active"] for r in rules)

def test_admin_creates_and_lists_camera(client, tenant):
    r = client.post(
        "/api/v1/cameras",
        json={"name": "Cocina", "rtsp_url": "rtsp://10.0.0.5/stream"},
        headers=tenant["admin"],
    )
    assert r.status_code == 201
    cam = r.json()
    assert cam["status"] == "offline"
    assert cam["restaurant_id"] == str(tenant["restaurant_id"])

    names = [c["name"] for c in client.get("/api/v1/cameras", headers=tenant["operator"]).json()]
    assert names == ["Cocina"]


def test_camera_response_does_not_expose_rtsp_url(client, tenant):
    cam = client.post(
        "/api/v1/cameras",
        json={"name": "Caja", "rtsp_url": "rtsp://user:secret@10.0.0.5/stream"},
        headers=tenant["admin"],
    ).json()
    assert "rtsp_url" not in cam
    listed = client.get("/api/v1/cameras", headers=tenant["admin"]).json()
    assert all("rtsp_url" not in c for c in listed)


def test_operator_cannot_create_camera(client, tenant):
    r = client.post("/api/v1/cameras", json={"name": "X"}, headers=tenant["operator"])
    assert r.status_code == 403


def test_update_camera(client, tenant):
    cam = client.post("/api/v1/cameras", json={"name": "A"}, headers=tenant["admin"]).json()
    r = client.patch(
        f"/api/v1/cameras/{cam['id']}", json={"name": "B", "fps": 10}, headers=tenant["admin"]
    )
    assert r.status_code == 200
    assert r.json()["name"] == "B" and r.json()["fps"] == 10


def test_delete_camera_is_soft_and_hides_it(client, tenant):
    cam = client.post("/api/v1/cameras", json={"name": "A"}, headers=tenant["admin"]).json()
    assert client.delete(f"/api/v1/cameras/{cam['id']}", headers=tenant["admin"]).status_code == 204
    assert client.get("/api/v1/cameras", headers=tenant["admin"]).json() == []


def test_unknown_camera_returns_404(client, tenant):
    r = client.get(
        "/api/v1/cameras/00000000-0000-0000-0000-000000000000", headers=tenant["admin"]
    )
    assert r.status_code == 404


def test_camera_isolated_between_restaurants(client, make_tenant):
    a, b = make_tenant(), make_tenant()
    cam = client.post("/api/v1/cameras", json={"name": "Privada"}, headers=a["admin"]).json()

    assert client.get("/api/v1/cameras", headers=b["admin"]).json() == []
    assert client.get(f"/api/v1/cameras/{cam['id']}", headers=b["admin"]).status_code == 404
    assert (
        client.patch(
            f"/api/v1/cameras/{cam['id']}", json={"name": "hack"}, headers=b["admin"]
        ).status_code
        == 404
    )
    assert client.delete(f"/api/v1/cameras/{cam['id']}", headers=b["admin"]).status_code == 404

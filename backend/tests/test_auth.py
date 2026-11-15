def test_health(client):
    assert client.get("/health").json()["status"] == "ok"


def test_seeded_admin_can_log_in(client):
    r = client.post(
        "/api/v1/auth/login", json={"email": "admin@saferest360.com", "password": "admin123"}
    )
    assert r.status_code == 200
    body = r.json()
    assert body["access_token"] and body["refresh_token"]


def test_wrong_password_is_rejected(client, tenant):
    r = client.post(
        "/api/v1/auth/login", json={"email": tenant["admin_email"], "password": "nope"}
    )
    assert r.status_code == 401


def test_unknown_email_is_rejected(client):
    r = client.post(
        "/api/v1/auth/login", json={"email": "nadie@saferest360.com", "password": "x"}
    )
    assert r.status_code == 401


def test_me_returns_current_user(client, tenant):
    r = client.get("/api/v1/auth/me", headers=tenant["operator"])
    assert r.status_code == 200
    assert r.json()["email"] == tenant["operator_email"]
    assert r.json()["role"] == "operator"
    assert "hashed_password" not in r.json()


def test_protected_route_requires_token(client):
    assert client.get("/api/v1/auth/me").status_code in (401, 403)


def test_garbage_token_is_rejected(client):
    r = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer not-a-jwt"})
    assert r.status_code == 401


def test_refresh_issues_new_access_token(client, tenant):
    login = client.post(
        "/api/v1/auth/login",
        json={"email": tenant["admin_email"], "password": "test-password-123"},
    ).json()
    r = client.post("/api/v1/auth/refresh", json={"refresh_token": login["refresh_token"]})
    assert r.status_code == 200
    me = client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {r.json()['access_token']}"}
    )
    assert me.status_code == 200


def test_access_token_cannot_be_used_as_refresh(client, tenant):
    access = tenant["admin"]["Authorization"].split()[1]
    r = client.post("/api/v1/auth/refresh", json={"refresh_token": access})
    assert r.status_code == 401


def test_refresh_token_cannot_be_used_as_access(client, tenant):
    login = client.post(
        "/api/v1/auth/login",
        json={"email": tenant["admin_email"], "password": "test-password-123"},
    ).json()
    r = client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {login['refresh_token']}"}
    )
    assert r.status_code == 401


def test_deactivated_user_cannot_log_in(client, tenant):
    me = client.get("/api/v1/auth/me", headers=tenant["operator"]).json()
    r = client.patch(
        f"/api/v1/users/{me['id']}", json={"is_active": False}, headers=tenant["admin"]
    )
    assert r.status_code == 200
    r = client.post(
        "/api/v1/auth/login",
        json={"email": tenant["operator_email"], "password": "test-password-123"},
    )
    assert r.status_code == 403
    assert client.get("/api/v1/auth/me", headers=tenant["operator"]).status_code == 401


def test_operator_cannot_manage_users(client, tenant):
    assert client.get("/api/v1/users", headers=tenant["operator"]).status_code == 403


def test_admin_lists_only_own_restaurant_users(client, make_tenant):
    a, b = make_tenant(), make_tenant()
    emails = {u["email"] for u in client.get("/api/v1/users", headers=a["admin"]).json()}
    assert emails == {a["admin_email"], a["operator_email"]}
    assert b["admin_email"] not in emails


def test_duplicate_email_is_rejected(client, tenant):
    r = client.post(
        "/api/v1/users",
        json={"email": tenant["operator_email"], "password": "x"},
        headers=tenant["admin"],
    )
    assert r.status_code == 400

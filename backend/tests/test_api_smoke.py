"""End-to-end API smoke tests (auth, tenant isolation, admin, analytics, exports).

Converted from the old scripts/smoke_test.py, which needed a live server; these
run in-process against the seeded demo store.
"""
import uuid

from conftest import ADMIN, auth


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "healthy"


def test_openapi_title(client):
    assert client.get("/openapi.json").json()["info"]["title"] == "Pairly API"


def test_authentication(client, admin_token, demo_token):
    assert client.post("/api/auth/login", json={"email": ADMIN[0], "password": "wrong"}).status_code == 401

    me = client.get("/api/auth/me", headers=auth(admin_token)).json()
    assert me["user"]["email"] == ADMIN[0]
    assert me["user"]["role"] == "super_admin"

    me = client.get("/api/auth/me", headers=auth(demo_token)).json()
    assert me["store"]["name"] == "Demo Store"

    r = client.post("/api/auth/forgot-password", json={"email": "nobody@example.com"})
    assert r.status_code == 200


def test_tenant_isolation_and_roles(client, admin_token, demo_token, demo_login):
    store_id = demo_login["store"]["id"]
    assert client.get("/api/admin/stores", headers=auth(demo_token)).status_code == 403
    assert client.get("/api/analytics/summary").status_code == 401

    r = client.get("/api/analytics/summary", headers=auth(demo_token))
    assert r.status_code == 200 and r.json()["data"]["total_revenue"] > 0

    assert client.get("/api/analytics/summary", headers=auth(admin_token)).status_code == 400
    assert client.get(f"/api/analytics/summary?store_id={store_id}", headers=auth(admin_token)).status_code == 200
    assert client.get("/api/analytics/summary?store_id=99999", headers=auth(admin_token)).status_code == 404


def test_admin_store_lifecycle(client, admin_token):
    h = auth(admin_token)
    email = f"smoke-{uuid.uuid4().hex[:8]}@example.com"
    r = client.post("/api/admin/stores", headers=h, json={
        "name": "Smoke Test Store",
        "manager_email": email,
        "manager_full_name": "Smoke Tester",
        "theme_mode": "dark",
        "brand_primary_color": "#10b981",
    })
    assert r.status_code == 201, r.text
    body = r.json()
    store_id, temp_password = body["store"]["id"], body.get("temp_password")
    assert body["manager"]["email"] == email

    assert client.post("/api/admin/stores", headers=h, json={"name": "Dup", "manager_email": email}).status_code == 409
    assert any(s["id"] == store_id for s in client.get("/api/admin/stores", headers=h).json()["items"])

    r = client.patch(f"/api/admin/stores/{store_id}", headers=h, json={"description": "Updated"})
    assert r.json()["description"] == "Updated"

    r = client.post(f"/api/admin/stores/{store_id}/disable", headers=h, json={"reason": "smoke test"})
    assert r.json()["is_active"] is False
    if temp_password:
        assert client.post("/api/auth/login", json={"email": email, "password": temp_password}).status_code == 403

    r = client.post(f"/api/admin/stores/{store_id}/enable", headers=h)
    assert r.json()["is_active"] is True
    if temp_password:
        assert client.post("/api/auth/login", json={"email": email, "password": temp_password}).status_code == 200

    assert client.get("/api/admin/stats", headers=h).json()["total_stores"] >= 2
    assert len(client.get("/api/admin/audit-log", headers=h).json()["items"]) > 0


def test_store_profile_and_datasets(client, demo_token):
    h = auth(demo_token)
    assert client.get("/api/store/profile", headers=h).json()["name"] == "Demo Store"
    r = client.patch("/api/store/profile", headers=h, json={"theme_mode": "light", "description": "Updated by tests"})
    assert r.json()["theme_mode"] == "light"
    assert len(client.get("/api/store/datasets", headers=h).json()["items"]) >= 1


def test_analytics_endpoints(client, demo_token):
    h = auth(demo_token)

    def ok(path):
        r = client.get(f"/api/analytics/{path}", headers=h)
        assert r.status_code == 200, (path, r.text)
        body = r.json()
        assert body.get("success"), (path, body)
        return body

    assert len(ok("top_products?limit=5")["products"]) > 0
    assert "countries" in ok("filters")["filters"]
    ok("revenue_by_country?limit=5")
    assert len(ok("seasonal_data")["monthly_data"]) > 0
    assert ok("frequent_itemsets?limit=10")["metadata"]["nodes_count"] > 0
    assert len(ok("association_rules?limit=10&min_support=0.01")["data"]) > 0
    assert len(ok("product_bundles_filtered?limit=10&min_support=0.01")["bundles"]) > 0


def test_scheduled_job(client, demo_token):
    h = auth(demo_token)
    assert client.get("/api/store/scheduled-job", headers=h).status_code == 200
    r = client.put("/api/store/scheduled-job", headers=h, json={"is_enabled": True, "cron_expression": "0 2 * * *"})
    assert r.json()["is_enabled"] is True
    r = client.put("/api/store/scheduled-job", headers=h, json={"is_enabled": False, "cron_expression": "0 2 * * *"})
    assert r.json()["is_enabled"] is False


def test_exports(client, demo_token):
    h = auth(demo_token)
    r = client.get("/api/store/exports/csv?type=summary", headers=h)
    assert r.status_code == 200 and "text/csv" in r.headers["content-type"]

    r = client.post("/api/store/exports/pdf", headers=h, json={"sections": ["summary", "top_products"]})
    assert r.status_code == 200
    pdf = client.get(r.json()["download_url"], headers=h)
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")

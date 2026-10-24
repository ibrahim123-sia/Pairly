"""End-to-end smoke test against a running backend on localhost:5000."""
import json
import sys
import time
import urllib.request
import urllib.error

BASE = "http://localhost:5000/api"


def call(method, path, token=None, body=None, expect=200):
    url = f"{BASE}{path}"
    data = None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if body is not None:
        data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            status = resp.status
            payload = resp.read()
            try:
                payload = json.loads(payload.decode() or "null")
            except Exception:
                payload = payload.decode(errors="replace")
            return status, payload
    except urllib.error.HTTPError as e:
        status = e.code
        try:
            payload = json.loads(e.read().decode())
        except Exception:
            payload = None
        return status, payload


passed = 0
failed = 0


def check(name, actual_status, expected_status, payload_check=None, payload=None):
    global passed, failed
    ok = actual_status == expected_status
    if ok and payload_check is not None:
        try:
            ok = payload_check(payload)
        except Exception:
            ok = False
    icon = "PASS" if ok else "FAIL"
    print(f"  [{icon}] {name} (status={actual_status}, expected={expected_status})")
    if ok:
        passed += 1
    else:
        failed += 1
        if payload is not None:
            print(f"        payload: {str(payload)[:200]}")


print("=" * 60)
print("PAIRLY - END TO END SMOKE TEST")
print("=" * 60)

print("\n[1] Public endpoints")
s, p = call("GET", "/health")
check("GET /api/health", s, 200, lambda x: x.get("status") == "healthy", p)

print("\n[2] Authentication")
s, p = call("POST", "/auth/login", body={"email": "admin@example.com", "password": "Admin@12345"})
check("Super admin login", s, 200, lambda x: x.get("access_token") and x["user"]["role"] == "super_admin", p)
admin_token = p["access_token"]

s, p = call("POST", "/auth/login", body={"email": "admin@example.com", "password": "wrong"})
check("Bad password rejected", s, 401, None, p)

s, p = call("POST", "/auth/login", body={"email": "demo@example.com", "password": "Demo@12345"})
check("Demo manager login", s, 200, lambda x: x.get("access_token") and x["user"]["role"] == "store_manager", p)
demo_token = p["access_token"]
demo_store_id = p["store"]["id"]

s, p = call("GET", "/auth/me", token=admin_token)
check("GET /auth/me as admin", s, 200, lambda x: x["user"]["email"] == "admin@example.com", p)

s, p = call("GET", "/auth/me", token=demo_token)
check("GET /auth/me as manager", s, 200, lambda x: x["store"] and x["store"]["name"] == "Demo Store", p)

s, p = call("POST", "/auth/forgot-password", body={"email": "nobody@example.com"})
check("Forgot password always 200", s, 200, None, p)

print("\n[3] Tenant isolation / role enforcement")
s, p = call("GET", "/admin/stores", token=demo_token)
check("Manager hits admin endpoint -> 403", s, 403, None, p)

s, p = call("GET", "/analytics/summary")
check("Anonymous hits analytics -> 401", s, 401, None, p)

s, p = call("GET", "/analytics/summary", token=demo_token)
check("Manager analytics summary -> 200", s, 200, lambda x: x.get("success") and x["data"]["total_revenue"] > 0, p)

s, p = call("GET", "/analytics/summary", token=admin_token)
check("Admin without store_id -> 400", s, 400, None, p)

s, p = call("GET", f"/analytics/summary?store_id={demo_store_id}", token=admin_token)
check("Admin viewing demo store via ?store_id= -> 200", s, 200, lambda x: x.get("success"), p)

s, p = call("GET", f"/analytics/summary?store_id=99999", token=admin_token)
check("Admin hits nonexistent store -> 404", s, 404, None, p)

print("\n[4] Admin: store CRUD")
test_email = f"smoke{int(time.time())}@test.local"
s, p = call("POST", "/admin/stores", token=admin_token, body={
    "name": "Smoke Test Store",
    "manager_email": test_email,
    "manager_full_name": "Smoke Tester",
    "theme_mode": "dark",
    "brand_primary_color": "#10b981",
})
check("Admin creates store + manager", s, 201, lambda x: x["store"]["slug"] and x["manager"]["email"] == test_email, p)
new_store_id = p["store"]["id"]
temp_password = p.get("temp_password")
print(f"        new store id={new_store_id}, temp_password={temp_password}")

s, p = call("POST", "/admin/stores", token=admin_token, body={
    "name": "Dup", "manager_email": test_email,
})
check("Duplicate manager email rejected", s, 409, None, p)

s, p = call("GET", "/admin/stores", token=admin_token)
check("List stores", s, 200, lambda x: any(item["id"] == new_store_id for item in x["items"]), p)

s, p = call("PATCH", f"/admin/stores/{new_store_id}", token=admin_token, body={"description": "Updated"})
check("Update store description", s, 200, lambda x: x["description"] == "Updated", p)

s, p = call("POST", f"/admin/stores/{new_store_id}/disable", token=admin_token, body={"reason": "smoke test disable"})
check("Disable store", s, 200, lambda x: x["is_active"] is False, p)

if temp_password:
    s, p = call("POST", "/auth/login", body={"email": test_email, "password": temp_password})
    check("Disabled store manager cannot log in -> 403", s, 403, None, p)

s, p = call("POST", f"/admin/stores/{new_store_id}/enable", token=admin_token)
check("Re-enable store", s, 200, lambda x: x["is_active"] is True, p)

if temp_password:
    s, p = call("POST", "/auth/login", body={"email": test_email, "password": temp_password})
    check("Re-enabled manager can log in", s, 200, None, p)

s, p = call("GET", "/admin/stats", token=admin_token)
check("Admin stats", s, 200, lambda x: x["total_stores"] >= 2, p)

s, p = call("GET", "/admin/audit-log", token=admin_token)
check("Audit log returns entries", s, 200, lambda x: len(x["items"]) > 0, p)

print("\n[5] Store manager: profile and analytics")
s, p = call("GET", "/store/profile", token=demo_token)
check("Manager profile", s, 200, lambda x: x["name"] == "Demo Store", p)

s, p = call("PATCH", "/store/profile", token=demo_token, body={"theme_mode": "light", "description": "Updated by smoke test"})
check("Manager updates profile", s, 200, lambda x: x["theme_mode"] == "light", p)

s, p = call("GET", "/store/datasets", token=demo_token)
check("Manager datasets list", s, 200, lambda x: len(x["items"]) >= 1, p)

s, p = call("GET", "/analytics/top_products?limit=5", token=demo_token)
check("Top products", s, 200, lambda x: x.get("success") and len(x["products"]) > 0, p)

s, p = call("GET", "/analytics/filters", token=demo_token)
check("Filters", s, 200, lambda x: x.get("success") and "countries" in x["filters"], p)

s, p = call("GET", "/analytics/revenue_by_country?limit=5", token=demo_token)
check("Revenue by country", s, 200, lambda x: x.get("success"), p)

s, p = call("GET", "/analytics/seasonal_data", token=demo_token)
check("Seasonal data", s, 200, lambda x: x.get("success") and len(x["monthly_data"]) > 0, p)

s, p = call("GET", "/analytics/frequent_itemsets?limit=10", token=demo_token)
check("Network graph", s, 200, lambda x: x.get("success") and x["metadata"]["nodes_count"] > 0, p)

print("\n  Running MBA (may take ~30s)...")
s, p = call("GET", "/analytics/association_rules?limit=10&min_support=0.01", token=demo_token)
check("Association rules", s, 200, lambda x: x.get("success"), p)

s, p = call("GET", "/analytics/product_bundles_filtered?limit=10&min_support=0.01", token=demo_token)
check("Product bundles", s, 200, lambda x: x.get("success"), p)

print("\n[6] Scheduled job")
s, p = call("GET", "/store/scheduled-job", token=demo_token)
check("Scheduled job initially null", s, 200, None, p)

s, p = call("PUT", "/store/scheduled-job", token=demo_token, body={"is_enabled": True, "cron_expression": "0 2 * * *"})
check("Create scheduled job", s, 200, lambda x: x["is_enabled"] is True, p)

s, p = call("PUT", "/store/scheduled-job", token=demo_token, body={"is_enabled": False, "cron_expression": "0 2 * * *"})
check("Disable scheduled job", s, 200, lambda x: x["is_enabled"] is False, p)

print("\n[7] Exports")
s, p = call("GET", "/store/exports/csv?type=summary", token=demo_token)
# CSV returns blob; our urllib will get 200 with non-JSON payload
check("CSV export status 200", s, 200, None, p)

s, p = call("POST", "/store/exports/pdf", token=demo_token, body={"sections": ["summary", "top_products"]})
check("PDF export generates id", s, 200, lambda x: x.get("export_id"), p)

print("\n" + "=" * 60)
print(f"RESULTS: {passed} passed, {failed} failed")
print("=" * 60)
sys.exit(0 if failed == 0 else 1)

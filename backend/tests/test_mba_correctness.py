"""Correctness checks for the market basket math and the insights endpoints.

Converted from the old scripts/mba_correctness_test.py (live-server script).
"""
import pytest

from conftest import auth


@pytest.fixture(scope="module")
def get(client, demo_token):
    def _get(path, **params):
        r = client.get(f"/api/analytics/{path}", headers=auth(demo_token), params=params)
        assert r.status_code == 200, (path, r.text)
        return r.json()
    return _get


def test_association_rule_math(get):
    rules = get("association_rules", limit=50, min_support=0.005, min_confidence=0.2)["data"]
    assert rules, "expected at least one rule"
    for r in rules:
        # confidence(A->B) = support(A,B) / support(A)
        assert abs(r["support"] / r["antecedent_support"] - r["confidence"]) < 0.02
        # lift = confidence / support(B)
        assert abs(r["confidence"] / r["consequent_support"] - r["lift"]) < 0.05
        assert r["lift"] >= 1.0
        assert 0 <= r["confidence"] <= 1
        assert 0 <= r["support"] <= 1
    # sorted by confidence desc (ties may differ after rounding to 3 decimals)
    assert all(rules[i]["confidence"] + 1e-3 >= rules[i + 1]["confidence"] for i in range(len(rules) - 1))


def test_recommendations(get):
    top = get("top_products", limit=1, sort_by="transactions")["products"][0]["description"]
    body = get("recommendations", product=top, limit=5)
    assert body["matched"] is True
    recs = body["recommendations"]
    assert recs
    assert all(r["lift"] > 0 and r["co_purchase_count"] > 0 for r in recs)
    assert all(abs(r["score"] - round(r["lift"] * r["confidence"], 3)) < 0.01 for r in recs)
    assert all(recs[i]["score"] >= recs[i + 1]["score"] for i in range(len(recs) - 1))


def test_rfm_segments(get):
    body = get("customer_segments")
    segs = body["segments"]
    assert segs and body["total_customers"] > 0
    assert sum(s["customers"] for s in segs) == body["total_customers"]
    assert 99 < sum(s["revenue_share"] for s in segs) < 101


def test_period_comparison(get):
    body = get("period_comparison", period_days=30)
    assert body["current_period"] and body["prior_period"]
    assert body["current_period"]["revenue"] >= 0
    assert isinstance(body["daily_revenue"], list)


def test_cohort_retention(get):
    cohorts = get("cohort_retention", max_periods=6)["cohorts"]
    assert cohorts
    assert cohorts[0]["retention"][0] == 100.0
    assert all(0 <= v <= 100 for v in cohorts[0]["retention"])


def test_bundle_simulator(client, demo_token, get):
    prods = [p["description"] for p in get("top_products", limit=2)["products"]]
    assert len(prods) == 2
    r = client.post("/api/analytics/bundle_simulator", headers=auth(demo_token),
                    json={"products": prods, "discount_pct": 15})
    assert r.status_code == 200
    body = r.json()
    assert "co_purchase_rate" in body["current"]
    assert "projected_bundle_revenue" in body["projected"]
    assert body["discount_pct"] == 15


def test_recommendations_csv_export(client, demo_token):
    r = client.get("/api/store/exports/csv?type=recommendations", headers=auth(demo_token))
    assert r.status_code == 200 and "text/csv" in r.headers["content-type"]
    lines = r.text.splitlines()
    assert len(lines) > 1
    expected = {"source_product", "recommended_product", "co_purchase_count", "confidence", "lift",
                "co_purchase_rate_pct", "score"}
    assert expected.issubset(set(lines[0].split(",")))

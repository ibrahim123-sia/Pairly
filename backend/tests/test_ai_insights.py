"""AI Insights card: generation, number check, retry, template fallback, cache, switches."""
import pytest

from app.models import AIUsageLog, Store
from app.services import dataset_service
from app.services.ai.insights import _texts, build_facts, template_insights
from app.services.ai.number_check import verify
from app.services.demo_service import DEMO_STORE_SLUG
from conftest import auth
from fakes import FakeGateway, insights_json, llm_down

pytestmark = pytest.mark.usefixtures("reset_ai")


@pytest.fixture(scope="module")
def facts(seeded):
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        store = db.query(Store).filter_by(slug=DEMO_STORE_SLUG).first()
        df, _ = dataset_service.get_active_dataframe(db, store)
        return build_facts(df)
    finally:
        db.close()


def _good(facts):
    r = facts["top_rules"][0]
    seg = facts["customer_segments"][0]
    return insights_json([
        {"kind": "bundle", "title": "Strongest pair",
         "text": f"{r['if_bought']} and {r['then_also_bought']} are bought together in "
                 f"{r['baskets_with_both_pct']}% of baskets.",
         "action": "Bundle them at 10% off."},
        {"kind": "cross_sell", "title": "Cross-sell",
         "text": f"{r['confidence_pct']}% of baskets with {r['if_bought']} also have {r['then_also_bought']}.",
         "action": "Show them side by side."},
        {"kind": "customers", "title": seg["segment"],
         "text": f"{seg['customers']} customers are {seg['segment']}.",
         "action": "Thank them with early access."},
    ])


def _bad():
    return insights_json([
        {"kind": "revenue", "title": "Growth", "text": "Revenue grew 987.65% last quarter.", "action": "Hire 7,777,777 staff."},
        {"kind": "bundle", "title": "Pair", "text": "Two items sell together.", "action": "Bundle them."},
        {"kind": "seasonal", "title": "Peak", "text": "Winter is busy.", "action": "Stock up."},
    ])


def _get(client, token, regenerate=False):
    if regenerate:
        return client.post("/api/ai/insights/regenerate", headers=auth(token))
    return client.get("/api/ai/insights", headers=auth(token))


def test_template_fallback_uses_only_fact_numbers(facts):
    items = template_insights(facts)
    assert 3 <= len(items) <= 5
    ok, bad = verify(_texts(items), facts)
    assert ok, bad
    assert all(i["title"] and i["text"] and i["action"] for i in items)


def test_facts_hold_no_customer_ids(facts):
    import json
    text = json.dumps(facts).lower()
    assert "customerid" not in text and "customer_id" not in text and "top_customers" not in text


def test_no_provider_gives_template(client, demo_token):
    body = _get(client, demo_token).json()
    assert body["source"] == "template"
    assert body["reason"] == "not_configured"
    assert body["verified"] is True
    assert 3 <= len(body["insights"]) <= 5


def test_ai_insights_are_verified_and_cached(client, demo_token, use_llm, db, facts):
    fake = use_llm(FakeGateway(replies=[_good(facts), _good(facts)]))

    first = _get(client, demo_token).json()
    assert first["source"] == "ai" and first["verified"] is True and first["cached"] is False
    assert len(fake.complete_calls) == 1

    second = _get(client, demo_token).json()
    assert second["cached"] is True and second["insights"] == first["insights"]
    assert len(fake.complete_calls) == 1, "cached result must not call the LLM"

    regen = _get(client, demo_token, regenerate=True).json()
    assert regen["cached"] is False and regen["source"] == "ai"
    assert len(fake.complete_calls) == 2

    logs = db.query(AIUsageLog).all()
    assert len(logs) == 2 and all(log.status == "ok" and log.total_tokens == 150 for log in logs)


def test_llm_receives_only_aggregated_facts(client, demo_token, use_llm, facts):
    fake = use_llm(FakeGateway(replies=[_good(facts)]))
    _get(client, demo_token)
    sent = fake.complete_calls[0][1]["content"].lower()
    assert "customerid" not in sent and "@" not in sent


def test_invented_number_is_retried_once(client, demo_token, use_llm, facts):
    fake = use_llm(FakeGateway(replies=[_bad(), _good(facts)]))
    body = _get(client, demo_token).json()
    assert body["source"] == "ai" and body["verified"] is True
    assert len(fake.complete_calls) == 2
    retry_prompt = fake.complete_calls[1][-1]["content"]
    assert "987.65%" in retry_prompt and "not in FACTS" in retry_prompt


def test_two_failed_checks_fall_back_to_template(client, demo_token, use_llm, db):
    fake = use_llm(FakeGateway(replies=[_bad(), _bad()]))
    body = _get(client, demo_token).json()
    assert body["source"] == "template" and body["reason"] == "check_failed"
    assert body["verified"] is True
    assert "987.65%" in body["unverified_numbers"]
    assert len(fake.complete_calls) == 2
    assert db.query(AIUsageLog).one().status == "fallback"


def test_unparseable_reply_falls_back(client, demo_token, use_llm):
    use_llm(FakeGateway(replies=["Sorry, I can't do that.", "still not json"]))
    assert _get(client, demo_token).json()["source"] == "template"


def test_llm_error_falls_back(client, demo_token, use_llm, db):
    use_llm(FakeGateway(replies=[llm_down()]))
    body = _get(client, demo_token).json()
    assert body["source"] == "template" and body["reason"] == "llm_error"
    assert db.query(AIUsageLog).one().status == "error"


def test_store_switch_off_skips_llm(client, demo_token, use_llm):
    fake = use_llm(FakeGateway(replies=[]))
    r = client.patch("/api/ai/settings", headers=auth(demo_token), json={"ai_enabled": False})
    assert r.status_code == 200 and r.json()["reason"] == "store_disabled"
    body = _get(client, demo_token).json()
    assert body["source"] == "template" and body["reason"] == "store_disabled"
    assert fake.complete_calls == []


def test_daily_limit_blocks_llm(client, demo_token, admin_token, use_llm, db, demo_login):
    fake = use_llm(FakeGateway(replies=[]))
    r = client.patch(f"/api/admin/ai/stores/{demo_login['store']['id']}", headers=auth(admin_token),
                     json={"daily_limit": 0})
    assert r.status_code == 200
    body = _get(client, demo_token).json()
    assert body["source"] == "template" and body["reason"] == "limit_reached"
    assert fake.complete_calls == []


def test_template_cache_is_replaced_once_ai_is_available(client, demo_token, use_llm, facts):
    assert _get(client, demo_token).json()["source"] == "template"  # no provider yet, cached
    use_llm(FakeGateway(replies=[_good(facts)]))
    assert _get(client, demo_token).json()["source"] == "ai"

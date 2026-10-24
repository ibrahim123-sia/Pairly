"""AI Insights card: 3-5 plain-English insights, each with a suggested action.

The analytics services compute every number. build_facts() collects their
aggregated results; the LLM only turns those facts into sentences. Every
number in the output is checked against the facts (number_check). If the
check fails we retry once, then fall back to template_insights(), which
writes the same kind of text from the facts without an LLM.

Results are cached in ai_insight_cache per store + dataset + thresholds.
"""
import hashlib
import json
import logging
import re
from datetime import datetime

from sqlalchemy.orm import Session

from app.models import AIInsightCache
from app.services import analytics_service, insights_service, mba_service
from app.services.ai import number_check, usage
from app.services.ai.llm_gateway import LLMError, Usage

logger = logging.getLogger("pairly.ai")

DISCOUNT_OPTIONS_PCT = [5, 10, 15]
KINDS = {"bundle", "cross_sell", "revenue", "customers", "seasonal"}
AT_RISK_SEGMENTS = ("At Risk", "Cannot Lose Them", "Hibernating")

SYSTEM_PROMPT = """You are Pairly, an analyst for a shop's market basket data.
You get a JSON object called FACTS. Every number in FACTS was computed by Pairly's analytics code.

Write 3 to 5 short insights for the store manager. Each insight has:
- "title": at most 8 words
- "text": one or two plain sentences that explain a finding
- "action": one concrete next step, e.g. a bundle, a promotion or a stock decision
- "kind": one of bundle, cross_sell, revenue, customers, seasonal

Strict rules:
- Use ONLY numbers that appear in FACTS. You may round them (78.6 -> 79) but never calculate new
  numbers: no sums, differences, ratios or projections.
- If you suggest a discount, use one of FACTS.suggested_discount_options_pct.
- Write any other count in words ("two products"), never as a digit.
- Percent fields end in _pct and are already percentages.
- Do not invent products, customers or dates. If FACTS has nothing for a topic, skip that topic.
- Plain English, no hype, no currency symbols.

Reply with JSON only, in this shape: {"insights": [{"title": "", "text": "", "action": "", "kind": ""}]}"""


# ---------------- facts ----------------

def build_facts(df, min_support=0.01, min_confidence=0.3, min_lift=1.0):
    """Aggregated, already-computed numbers. Nothing per-customer."""
    summary = analytics_service.compute_summary(df)
    rules = mba_service.compute_association_rules(df, min_support, min_confidence, min_lift, 5).get("data", [])
    bundles = mba_service.compute_product_bundles(df, min_support, min_confidence, min_lift, 5).get("bundles", [])
    top = analytics_service.compute_top_products(df, "revenue", 5).get("products", [])
    countries = analytics_service.compute_revenue_by_country(df, "all", "all", 3).get("revenue_analysis", [])
    seasonal = analytics_service.compute_seasonal(df).get("metadata", {})
    rfm = insights_service.compute_rfm(df)

    return {
        "overview": {
            "baskets": summary.get("total_transactions"),
            "products": summary.get("total_products"),
            "revenue": round(summary.get("total_revenue") or 0, 2),
            "avg_basket_value": summary.get("avg_transaction_value"),
            "multi_item_baskets_pct": summary.get("multi_item_percentage"),
            "date_from": (summary.get("date_range") or {}).get("start"),
            "date_to": (summary.get("date_range") or {}).get("end"),
        },
        "top_rules": [
            {
                "if_bought": r["antecedent"],
                "then_also_bought": r["consequent"],
                "confidence_pct": round(r["confidence"] * 100, 1),
                "baskets_with_both_pct": round(r["support"] * 100, 1),
                "lift": round(r["lift"], 1),
            }
            for r in rules
        ],
        "top_bundles": [
            {
                "products": b["products"],
                "baskets_with_both": b["transaction_count"],
                "confidence_pct": round(b["confidence"] * 100, 1),
                "lift": round(b["lift"], 1),
            }
            for b in bundles
        ],
        "top_products_by_revenue": [
            {"product": p["description"], "revenue": round(p["total_revenue"], 2), "revenue_share_pct": p["revenue_share"]}
            for p in top
        ],
        "top_countries": [
            {"country": c["country"], "revenue": round(c["total_revenue"], 2), "share_pct": round(c["market_share"], 1)}
            for c in countries
        ],
        "seasonality": {
            "peak_month": seasonal.get("peak_month"),
            "peak_weekday": seasonal.get("peak_weekday"),
            "peak_hour": seasonal.get("peak_hour"),
        },
        "customer_segments": [
            {
                "segment": s["segment"],
                "customers": s["customers"],
                "revenue_share_pct": s["revenue_share"],
                "avg_days_since_last_order": s["avg_recency_days"],
            }
            for s in rfm.get("segments", [])
        ],
        "suggested_discount_options_pct": DISCOUNT_OPTIONS_PCT,
    }


# ---------------- template fallback ----------------

def _fmt(x):
    if x is None:
        return "0"
    if float(x).is_integer():
        return f"{int(x):,}"
    return f"{x:,.1f}"


def template_insights(facts):
    """Deterministic insights from the facts. Uses only fact numbers, so it always passes the check."""
    out = []
    rules = facts.get("top_rules") or []
    if rules:
        r = rules[0]
        out.append({
            "kind": "bundle",
            "title": "Strongest product pair",
            "text": f"{r['if_bought']} and {r['then_also_bought']} are bought together in "
                    f"{_fmt(r['baskets_with_both_pct'])}% of baskets. When a basket has {r['if_bought']}, "
                    f"it also has {r['then_also_bought']} {_fmt(r['confidence_pct'])}% of the time.",
            "action": f"Offer them as a bundle at {DISCOUNT_OPTIONS_PCT[1]}% off and place them side by side.",
        })
    if len(rules) > 1:
        r = rules[1]
        out.append({
            "kind": "cross_sell",
            "title": f"Suggest {r['then_also_bought'].title()[:40]}",
            "text": f"{_fmt(r['confidence_pct'])}% of baskets with {r['if_bought']} also contain "
                    f"{r['then_also_bought']} (lift {_fmt(r['lift'])}).",
            "action": f"Show {r['then_also_bought']} as a 'goes well with' suggestion next to {r['if_bought']}.",
        })
    top = facts.get("top_products_by_revenue") or []
    if top:
        p = top[0]
        out.append({
            "kind": "revenue",
            "title": "Top revenue product",
            "text": f"{p['product']} brings in {_fmt(p['revenue_share_pct'])}% of revenue, more than any other product.",
            "action": "Keep it well stocked and use it as the anchor item in bundles.",
        })
    segs = {s["segment"]: s for s in facts.get("customer_segments") or []}
    risk = next((segs[n] for n in AT_RISK_SEGMENTS if n in segs), None)
    if risk:
        out.append({
            "kind": "customers",
            "title": f"{risk['segment']} customers",
            "text": f"{_fmt(risk['customers'])} customers are in the '{risk['segment']}' segment. They last ordered "
                    f"about {_fmt(risk['avg_days_since_last_order'])} days ago on average and bring "
                    f"{_fmt(risk['revenue_share_pct'])}% of revenue.",
            "action": f"Send them a win-back offer, for example {DISCOUNT_OPTIONS_PCT[1]}% off their next order.",
        })
    peak = (facts.get("seasonality") or {}).get("peak_month")
    if peak:
        out.append({
            "kind": "seasonal",
            "title": f"{peak} is the busiest month",
            "text": f"Across the data, {peak} has the highest revenue of any month.",
            "action": f"Plan stock and bundle promotions ahead of {peak}.",
        })
    return out[:5]


# ---------------- LLM generation ----------------

def _parse(content):
    """Pull the insights list out of the model reply, tolerating code fences or extra text."""
    if not content:
        return None
    text = content.strip()
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return None
    try:
        data = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None
    items = data.get("insights") if isinstance(data, dict) else None
    if not isinstance(items, list):
        return None
    clean = []
    for it in items[:5]:
        if not isinstance(it, dict):
            continue
        title, text, action = (str(it.get(k) or "").strip() for k in ("title", "text", "action"))
        if not text:
            continue
        kind = str(it.get("kind") or "").strip().lower()
        clean.append({"title": title[:120], "text": text[:600], "action": action[:300],
                      "kind": kind if kind in KINDS else "revenue"})
    return clean if len(clean) >= 3 else None


def _texts(insights):
    return [x for i in insights for x in (i["title"], i["text"], i["action"])]


def generate_with_llm(gateway, facts):
    """Returns (insights or None, usage, llm_calls, last_unverified)."""
    total = Usage()
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": "FACTS:\n" + json.dumps(facts, ensure_ascii=False)},
    ]
    bad = []
    for attempt in (1, 2):
        resp = gateway.complete(messages, json_mode=True)
        total.add(resp.usage)
        insights = _parse(resp.content)
        if insights is None:
            bad = ["(reply was not valid insights JSON)"]
        else:
            ok, bad = number_check.verify(_texts(insights), facts)
            if ok:
                return insights, total, attempt, []
        logger.info("AI insights failed the number check (attempt %s): %s", attempt, bad[:10])
        messages += [
            {"role": "assistant", "content": resp.content or ""},
            {"role": "user", "content": "These numbers are not in FACTS: " + ", ".join(bad[:20])
             + ". Rewrite the insights using only numbers that appear in FACTS. Reply with JSON only."},
        ]
    return None, total, 2, bad


def params_key(min_support, min_confidence, min_lift):
    raw = json.dumps({"s": round(min_support, 4), "c": round(min_confidence, 4), "l": round(min_lift, 4)})
    return hashlib.sha1(raw.encode()).hexdigest()


def get_insights(db: Session, store, user, df, dataset, gateway, min_support=0.01, min_confidence=0.3,
                 min_lift=1.0, regenerate=False):
    key = params_key(min_support, min_confidence, min_lift)
    status = usage.status_for(db, store, gateway)
    cached = db.query(AIInsightCache).filter_by(store_id=store.id, dataset_id=dataset.id, params_key=key).first()

    # Serve the cache unless asked to regenerate, or unless it is a template
    # made only because AI was off and AI is available now.
    if cached and not regenerate:
        made_without_ai = cached.payload.get("source") == "template" and cached.payload.get("reason") != "check_failed"
        if not (made_without_ai and status.available):
            return {**cached.payload, "cached": True, "ai_status": status.to_dict()}

    facts = build_facts(df, min_support, min_confidence, min_lift)
    payload = {
        "params": {"min_support": min_support, "min_confidence": min_confidence, "min_lift": min_lift},
        "dataset_id": dataset.id,
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }

    insights = None
    if status.available:
        try:
            insights, used, calls, bad = generate_with_llm(gateway, facts)
        except LLMError as exc:
            logger.warning("AI insights LLM call failed for store %s: %s", store.id, exc)
            usage.log_usage(db, store.id, getattr(user, "id", None), "insights", gateway, "error")
            payload.update(source="template", reason="llm_error")
        else:
            usage.log_usage(db, store.id, getattr(user, "id", None), "insights", gateway,
                            "ok" if insights else "fallback", used, calls)
            if insights:
                payload.update(source="ai", provider=gateway.provider, model=gateway.model, verified=True)
            else:
                payload.update(source="template", reason="check_failed", unverified_numbers=bad[:20])
    else:
        payload.update(source="template", reason=status.reason)

    if insights is None:
        insights = template_insights(facts)
        payload["verified"] = number_check.verify(_texts(insights), facts)[0]
    payload["insights"] = insights

    if cached:
        cached.payload = payload
        cached.created_at = datetime.utcnow()
    else:
        db.add(AIInsightCache(store_id=store.id, dataset_id=dataset.id, params_key=key, payload=payload))
    db.commit()
    return {**payload, "cached": False, "ai_status": usage.status_for(db, store, gateway).to_dict()}

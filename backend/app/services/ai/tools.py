"""Read-only tools the "Ask Pairly" assistant can call.

Each tool wraps an existing analytics service and runs on the active dataset
of ToolContext.store, the store of the signed-in user, resolved on the server.
The model never chooses the store: tool schemas have no store argument, and
any argument not declared in a schema (such as "store_id") is dropped.

Tools return aggregated results only (rules, bundle stats, segment totals).
Customer ids and other per-customer rows are never returned.
"""
import json
import logging
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models import Store
from app.services import analytics_service, cache_service, dataset_service, insights_service, mba_service

logger = logging.getLogger("pairly.ai")

# Keys that could identify a customer. Stripped from every tool result as a last line of defence.
_PRIVATE_KEYS = {"customerid", "customer_id", "top_customers", "customers_list", "email", "customer_email"}


@dataclass
class ToolContext:
    db: Session
    store: Store


class NoDataError(Exception):
    pass


def _frame(ctx: ToolContext):
    df, dataset = dataset_service.get_active_dataframe(ctx.db, ctx.store)
    if df is None:
        raise NoDataError("This store has no active dataset yet. Upload data on the My Datasets page.")
    return df, dataset


def _cached(ctx, name, args, builder):
    df, dataset = _frame(ctx)
    key = cache_service.make_key(ctx.store.id, dataset.id, f"ai_tool:{name}", args)
    return cache_service.get_or_set(key, lambda: builder(df))


def _pct(x, nd=1):
    return round(float(x) * 100, nd)


def _clamp(v, lo, hi, default):
    try:
        return max(lo, min(hi, type(default)(v)))
    except (TypeError, ValueError):
        return default


def _match(text, needle):
    return needle.lower() in str(text).lower()


def scrub(obj):
    """Remove customer-identifying keys anywhere in a result."""
    if isinstance(obj, dict):
        return {k: scrub(v) for k, v in obj.items() if str(k).lower() not in _PRIVATE_KEYS}
    if isinstance(obj, list):
        return [scrub(v) for v in obj]
    return obj


# ---------------- tool implementations ----------------

def get_association_rules(ctx, product=None, min_confidence=0.3, min_lift=1.0, limit=10):
    min_confidence = _clamp(min_confidence, 0.1, 1.0, 0.3)
    min_lift = _clamp(min_lift, 0.5, 100.0, 1.0)
    limit = _clamp(limit, 1, 20, 10)

    def build(df):
        res = mba_service.compute_association_rules(df, 0.01, min_confidence, min_lift, 100)
        return res.get("data", []), res.get("metadata", {})

    rules, meta = _cached(ctx, "rules", {"c": min_confidence, "l": min_lift}, build)
    if product:
        rules = [r for r in rules if _match(r["antecedent"], product) or _match(r["consequent"], product)]
    return {
        "product_filter": product,
        "rules_found": len(rules),
        "baskets_analysed": (meta.get("filter_stats") or {}).get("transactions_in_analysis"),
        "rules": [
            {
                "if_bought": r["antecedent"],
                "then_also_bought": r["consequent"],
                "confidence_pct": _pct(r["confidence"]),
                "baskets_with_both_pct": _pct(r["support"], 2),
                "lift": round(r["lift"], 2),
            }
            for r in rules[:limit]
        ],
        "note": "Rules come from the 100 best-selling products. confidence_pct = share of baskets with the "
                "first product that also contain the second.",
    }


def get_bundles(ctx, product=None, limit=10):
    limit = _clamp(limit, 1, 20, 10)

    def build(df):
        return mba_service.compute_product_bundles(df, 0.01, 0.3, 1.0, 100).get("bundles", [])

    bundles = _cached(ctx, "bundles", {}, build)
    if product:
        bundles = [b for b in bundles if any(_match(p, product) for p in b["products"])]
    return {
        "product_filter": product,
        "bundles_found": len(bundles),
        "bundles": [
            {
                "products": b["products"],
                "baskets_with_both": b["transaction_count"],
                "baskets_with_both_pct": _pct(b["support"], 2),
                "confidence_pct": _pct(b["confidence"]),
                "lift": b["lift"],
            }
            for b in bundles[:limit]
        ],
    }


def get_recommendations_for_product(ctx, product, limit=5):
    if not product or not str(product).strip():
        return {"error": "product is required"}
    product = str(product).strip()
    limit = _clamp(limit, 1, 15, 5)
    res = _cached(ctx, "recs", {"p": product.lower(), "n": limit},
                  lambda df: insights_service.compute_recommendations(df, product, limit))
    if not res.get("matched"):
        return {"product": product, "matched": False,
                "note": "No product with that name was found in this store's data."}
    meta = res.get("metadata") or {}
    return {
        "product": res.get("target"),
        "matched": True,
        "baskets_with_product": meta.get("target_transactions"),
        "recommendations": [
            {
                "product": r["product"],
                "baskets_with_both": r["co_purchase_count"],
                "also_bought_pct": r["co_purchase_rate"],
                "lift": r["lift"],
            }
            for r in res.get("recommendations", [])
        ],
    }


def get_revenue_breakdown(ctx, year="all", limit=10):
    limit = _clamp(limit, 1, 20, 10)
    year = str(year or "all")
    res = _cached(ctx, "revenue", {"y": year, "n": limit},
                  lambda df: analytics_service.compute_revenue_by_country(df, "all", year, limit))
    meta = res.get("metadata") or {}
    return {
        "year": year,
        "total_revenue": round(meta.get("global_total_revenue") or 0, 2),
        "countries_with_sales": meta.get("total_countries"),
        "by_country": [
            {
                "country": r["country"],
                "revenue": round(r["total_revenue"], 2),
                "share_pct": round(r["market_share"], 1),
                "orders": r["transaction_count"],
                "customers": r["customer_count"],
            }
            for r in res.get("revenue_analysis", [])
        ],
    }


def get_seasonal_trend(ctx, product=None):
    if product:
        res = _cached(ctx, "season_p", {"p": str(product).lower()},
                      lambda df: analytics_service.compute_seasonal_product(df, product, "all", "all"))
        monthly = res.get("monthly_data", [])
        if not monthly:
            return {"product": product, "matched": False,
                    "note": "No sales found for that product name."}
        peak = max(monthly, key=lambda m: m["revenue"])
        return {
            "product": product,
            "matched": True,
            "total_revenue": round((res.get("metadata") or {}).get("total_revenue") or 0, 2),
            "peak_month": peak["month_name"],
            "monthly": [{"month": m["month_name"], "revenue": round(m["revenue"], 2), "orders": m["transactions"]}
                        for m in monthly],
        }
    res = _cached(ctx, "season", {}, analytics_service.compute_seasonal)
    meta = res.get("metadata") or {}
    return {
        "peak_month": meta.get("peak_month"),
        "peak_weekday": meta.get("peak_weekday"),
        "peak_hour": meta.get("peak_hour"),
        "monthly": [
            {"month": m["month_name"], "revenue": round(m["revenue"], 2), "orders": m["transactions"],
             "revenue_share_pct": m["revenue_share"]}
            for m in res.get("monthly_data", [])
        ],
        "note": "Months are combined across all years in the dataset.",
    }


def get_rfm_segments(ctx):
    res = _cached(ctx, "rfm", {}, insights_service.compute_rfm)
    if res.get("error"):
        return {"error": res["error"]}
    return {
        "as_of": res.get("as_of"),
        "total_customers": res.get("total_customers"),
        "segments": [
            {
                "segment": s["segment"],
                "customers": s["customers"],
                "revenue": round(s["total_revenue"], 2),
                "revenue_share_pct": s["revenue_share"],
                "avg_days_since_last_order": s["avg_recency_days"],
                "avg_orders": s["avg_frequency"],
                "avg_spend": s["avg_monetary"],
            }
            for s in res.get("segments", [])
        ],
        "note": "Customers at risk of leaving are usually in 'At Risk', 'Cannot Lose Them' and 'Hibernating'. "
                "Only segment totals are available here; the customer list is on the Customers page.",
    }


def get_top_products(ctx, sort_by="revenue", limit=10):
    sort_by = sort_by if sort_by in ("revenue", "transactions", "customers", "quantity") else "revenue"
    limit = _clamp(limit, 1, 20, 10)
    res = _cached(ctx, "top", {"s": sort_by, "n": limit},
                  lambda df: analytics_service.compute_top_products(df, sort_by, limit))
    return {
        "sorted_by": sort_by,
        "products": [
            {
                "rank": p["rank"],
                "product": p["description"],
                "revenue": round(p["total_revenue"], 2),
                "revenue_share_pct": p["revenue_share"],
                "orders": p["transactions"],
                "units": p["total_quantity"],
                "customers": p["customers"],
            }
            for p in res.get("products", [])
        ],
    }


# ---------------- registry ----------------

def _schema(properties=None, required=None):
    return {"type": "object", "properties": properties or {}, "required": required or [],
            "additionalProperties": False}


_PRODUCT = {"type": "string", "description": "Part of a product name, e.g. 'coffee' or 'teacup'. Case-insensitive."}
_LIMIT = {"type": "integer", "minimum": 1, "maximum": 20}

TOOLS = {
    "get_association_rules": (
        get_association_rules,
        "Association rules: 'customers who buy X also buy Y', with confidence, lift and how many baskets "
        "contain both. Optionally only rules that mention a product.",
        _schema({"product": _PRODUCT, "min_confidence": {"type": "number", "minimum": 0.1, "maximum": 1},
                 "min_lift": {"type": "number", "minimum": 0.5}, "limit": _LIMIT}),
    ),
    "get_bundles": (
        get_bundles,
        "Recommended two-product bundles ranked by confidence and lift. Optionally only bundles with a product.",
        _schema({"product": _PRODUCT, "limit": _LIMIT}),
    ),
    "get_recommendations_for_product": (
        get_recommendations_for_product,
        "Products most often bought together with one product (cross-sell suggestions).",
        _schema({"product": _PRODUCT, "limit": {"type": "integer", "minimum": 1, "maximum": 15}}, ["product"]),
    ),
    "get_revenue_breakdown": (
        get_revenue_breakdown,
        "Revenue by country with share, orders and customers. Optionally for one year.",
        _schema({"year": {"type": "string", "description": "A year like '2011', or 'all'"}, "limit": _LIMIT}),
    ),
    "get_seasonal_trend": (
        get_seasonal_trend,
        "Revenue by month and the peak month, weekday and hour. Optionally for one product.",
        _schema({"product": _PRODUCT}),
    ),
    "get_rfm_segments": (
        get_rfm_segments,
        "Customer segments from RFM (recency, frequency, monetary): how many customers per segment, their "
        "revenue and how long since they last ordered. Use for loyalty and churn questions.",
        _schema(),
    ),
    "get_top_products": (
        get_top_products,
        "Best-selling products ranked by revenue, transactions, customers or quantity.",
        _schema({"sort_by": {"type": "string", "enum": ["revenue", "transactions", "customers", "quantity"]},
                 "limit": _LIMIT}),
    ),
}


def tool_specs():
    """Tool definitions in the OpenAI function-calling format."""
    return [
        {"type": "function", "function": {"name": name, "description": desc, "parameters": params}}
        for name, (_, desc, params) in TOOLS.items()
    ]


def parse_arguments(name, raw):
    """Parse model arguments and keep only the parameters the tool declares."""
    try:
        args = json.loads(raw) if isinstance(raw, str) and raw.strip() else (raw or {})
    except json.JSONDecodeError:
        args = {}
    if not isinstance(args, dict):
        args = {}
    allowed = TOOLS[name][2]["properties"].keys()
    return {k: v for k, v in args.items() if k in allowed and v is not None}


def run_tool(ctx: ToolContext, name, raw_args):
    """Run a tool by name for the context's store. Always returns a JSON-safe dict."""
    if name not in TOOLS:
        return {"error": f"Unknown tool '{name}'."}
    args = parse_arguments(name, raw_args)
    try:
        result = TOOLS[name][0](ctx, **args)
    except NoDataError as exc:
        return {"error": str(exc)}
    except Exception:
        logger.exception("AI tool %s failed for store %s", name, ctx.store.id)
        return {"error": "The analysis failed for this question."}
    return scrub(result)

"""High-value retail insights for real stores: cross-sell recommendations,
RFM customer segmentation, period-over-period KPIs, cohort retention,
and bundle simulation."""
from datetime import timedelta
import pandas as pd
import numpy as np


# ---------- Cross-sell recommendations ----------

def compute_recommendations(df, product_name=None, limit=10, min_co_occurrence=3):
    """For a target product (or all top products), return top N items most
    frequently co-purchased, ranked by lift x confidence.

    Returns either a list of recommendations for the target product, or a
    dict {product: [recs]} when product_name is None (top 50 products).
    """
    if df is None or "Description" not in df.columns or "InvoiceNo" not in df.columns:
        return {"target": product_name, "recommendations": [], "error": "missing columns"}

    if product_name:
        target_match = df[df["Description"].astype(str).str.lower() == product_name.lower()]
        if len(target_match) == 0:
            similar = df[df["Description"].astype(str).str.lower().str.contains(product_name.lower(), na=False)]
            if len(similar) == 0:
                return {"target": product_name, "recommendations": [], "matched": False}
            target_name = similar["Description"].mode().iloc[0]
        else:
            target_name = product_name if product_name in df["Description"].values else target_match["Description"].mode().iloc[0]

        return _recommendations_for_product(df, target_name, limit, min_co_occurrence)

    top_products = df["Description"].value_counts().head(50).index.tolist()
    lookups = _product_lookups(df)
    out = {}
    for prod in top_products:
        out[prod] = _recommendations_for_product(df, prod, limit, min_co_occurrence, lookups)["recommendations"]
    return {"per_product": out, "total_products": len(out)}


def _product_lookups(df):
    """Per-product revenue and invoice sets. Built once and shared when many
    products are scored, since building them is the expensive part."""
    revenue_by_product = (
        df.groupby("Description")["TotalAmount"].sum().to_dict()
        if "TotalAmount" in df.columns else {}
    )
    invoices_by_product = df.groupby("Description")["InvoiceNo"].apply(lambda s: set(s.unique())).to_dict()
    return revenue_by_product, invoices_by_product


def _recommendations_for_product(df, target_name, limit, min_co_occurrence, lookups=None):
    target_invoices = set(df[df["Description"] == target_name]["InvoiceNo"].unique())
    target_support_count = len(target_invoices)
    total_invoices = df["InvoiceNo"].nunique()
    if target_support_count == 0 or total_invoices == 0:
        return {"target": target_name, "recommendations": [], "matched": False}

    co_purchases = df[df["InvoiceNo"].isin(target_invoices)]
    co_counts = co_purchases[co_purchases["Description"] != target_name]["Description"].value_counts()
    co_counts = co_counts[co_counts >= min_co_occurrence].head(limit * 3)

    revenue_by_product, invoices_by_product = lookups or _product_lookups(df)

    recs = []
    for other_name, co_count in co_counts.items():
        b_invoices = invoices_by_product.get(other_name, set())
        b_support = len(b_invoices)
        if b_support == 0:
            continue
        support_ab = co_count / total_invoices
        support_a = target_support_count / total_invoices
        support_b = b_support / total_invoices
        confidence = co_count / target_support_count
        lift = confidence / support_b if support_b > 0 else 0
        score = float(lift * confidence)
        recs.append({
            "product": other_name,
            "co_purchase_count": int(co_count),
            "support": round(support_ab, 4),
            "confidence": round(confidence, 3),
            "lift": round(lift, 2),
            "score": round(score, 3),
            "co_purchase_rate": round(co_count / target_support_count * 100, 1),
            "product_revenue": round(float(revenue_by_product.get(other_name, 0.0)), 2),
        })
    recs.sort(key=lambda r: r["score"], reverse=True)
    return {
        "target": target_name,
        "matched": True,
        "recommendations": recs[:limit],
        "metadata": {
            "target_transactions": target_support_count,
            "total_transactions": total_invoices,
            "target_support": round(target_support_count / total_invoices, 4),
        },
    }


# ---------- RFM customer segmentation ----------

SEGMENT_RULES = [
    ("Champions",       lambda r, f, m: r >= 4 and f >= 4 and m >= 4),
    ("Loyal Customers", lambda r, f, m: r >= 3 and f >= 3),
    ("Potential Loyalists", lambda r, f, m: r >= 4 and f <= 3),
    ("New Customers",   lambda r, f, m: r >= 4 and f == 1),
    ("Big Spenders",    lambda r, f, m: m >= 4 and r >= 2),
    ("At Risk",         lambda r, f, m: r <= 2 and f >= 3),
    ("Cannot Lose Them",lambda r, f, m: r <= 2 and f >= 4 and m >= 4),
    ("Hibernating",     lambda r, f, m: r <= 2 and f <= 2),
    ("Lost",            lambda r, f, m: r == 1 and f == 1),
]


def _label_segment(r, f, m):
    for name, rule in SEGMENT_RULES:
        if rule(r, f, m):
            return name
    return "Others"


def compute_rfm(df, as_of=None):
    if df is None or "CustomerID" not in df.columns or "InvoiceNo" not in df.columns:
        return {"segments": [], "customers": [], "error": "missing customer or invoice columns"}

    df = df.copy()
    if "InvoiceDate" in df.columns:
        df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"], errors="coerce")
    elif "Year" in df.columns and "Month" in df.columns:
        df["InvoiceDate"] = pd.to_datetime(dict(year=df["Year"], month=df["Month"], day=df.get("Day", 1)), errors="coerce")
    else:
        return {"segments": [], "customers": [], "error": "no date information"}

    df = df[df["CustomerID"].astype(str).str.lower() != "unknown"]
    df = df[df["InvoiceDate"].notna()]
    if len(df) == 0:
        return {"segments": [], "customers": [], "error": "no valid customer data"}

    if as_of is None:
        as_of = df["InvoiceDate"].max() + pd.Timedelta(days=1)
    else:
        as_of = pd.to_datetime(as_of)

    rfm = df.groupby("CustomerID").agg(
        last_purchase=("InvoiceDate", "max"),
        frequency=("InvoiceNo", "nunique"),
        monetary=("TotalAmount", "sum"),
    ).reset_index()
    rfm["recency_days"] = (as_of - rfm["last_purchase"]).dt.days

    def _qscore(series, ascending=True, q=5):
        try:
            return pd.qcut(series.rank(method="first", ascending=ascending), q, labels=range(1, q + 1)).astype(int)
        except ValueError:
            return pd.Series([3] * len(series), index=series.index)

    rfm["R"] = _qscore(rfm["recency_days"], ascending=False)
    rfm["F"] = _qscore(rfm["frequency"], ascending=True)
    rfm["M"] = _qscore(rfm["monetary"], ascending=True)
    rfm["segment"] = rfm.apply(lambda r: _label_segment(int(r["R"]), int(r["F"]), int(r["M"])), axis=1)

    seg_summary = rfm.groupby("segment").agg(
        customers=("CustomerID", "count"),
        total_revenue=("monetary", "sum"),
        avg_recency=("recency_days", "mean"),
        avg_frequency=("frequency", "mean"),
        avg_monetary=("monetary", "mean"),
    ).reset_index().sort_values("total_revenue", ascending=False)

    segments = []
    total_rev = float(seg_summary["total_revenue"].sum())
    for _, row in seg_summary.iterrows():
        segments.append({
            "segment": row["segment"],
            "customers": int(row["customers"]),
            "total_revenue": float(row["total_revenue"]),
            "revenue_share": round(float(row["total_revenue"]) / total_rev * 100, 1) if total_rev else 0,
            "avg_recency_days": round(float(row["avg_recency"]), 1),
            "avg_frequency": round(float(row["avg_frequency"]), 2),
            "avg_monetary": round(float(row["avg_monetary"]), 2),
        })

    top_customers = rfm.nlargest(25, "monetary")[
        ["CustomerID", "recency_days", "frequency", "monetary", "R", "F", "M", "segment"]
    ].to_dict("records")
    for c in top_customers:
        c["CustomerID"] = str(c["CustomerID"])
        c["monetary"] = round(float(c["monetary"]), 2)
        c["recency_days"] = int(c["recency_days"])
        c["frequency"] = int(c["frequency"])
        c["R"] = int(c["R"]); c["F"] = int(c["F"]); c["M"] = int(c["M"])

    return {
        "as_of": as_of.strftime("%Y-%m-%d"),
        "total_customers": int(len(rfm)),
        "segments": segments,
        "top_customers": top_customers,
    }


# ---------- Period-over-period ----------

def compute_period_comparison(df, period_days=30, end_date=None):
    if df is None or "InvoiceDate" not in df.columns:
        if "Year" in df.columns and "Month" in df.columns:
            df = df.copy()
            df["InvoiceDate"] = pd.to_datetime(dict(year=df["Year"], month=df["Month"], day=df.get("Day", 1)), errors="coerce")
        else:
            return {"error": "no date information"}

    df = df.copy()
    df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"], errors="coerce")
    df = df[df["InvoiceDate"].notna()]
    if len(df) == 0:
        return {"error": "no valid date data"}

    end = pd.to_datetime(end_date) if end_date else df["InvoiceDate"].max()
    current_start = end - pd.Timedelta(days=period_days - 1)
    prior_end = current_start - pd.Timedelta(days=1)
    prior_start = prior_end - pd.Timedelta(days=period_days - 1)

    cur = df[(df["InvoiceDate"] >= current_start) & (df["InvoiceDate"] <= end)]
    prior = df[(df["InvoiceDate"] >= prior_start) & (df["InvoiceDate"] <= prior_end)]

    def _kpis(d):
        rev = float(d["TotalAmount"].sum()) if "TotalAmount" in d.columns else 0.0
        tx = int(d["InvoiceNo"].nunique()) if "InvoiceNo" in d.columns else 0
        cust = int(d["CustomerID"].nunique()) if "CustomerID" in d.columns else 0
        units = int(d["Quantity"].sum()) if "Quantity" in d.columns else 0
        aov = rev / tx if tx else 0
        return {"revenue": rev, "transactions": tx, "customers": cust, "units": units, "avg_order_value": round(aov, 2)}

    cur_k = _kpis(cur)
    prior_k = _kpis(prior)

    def _delta(a, b):
        if b == 0:
            return None if a == 0 else 100.0
        return round((a - b) / b * 100, 1)

    deltas = {k: _delta(cur_k[k], prior_k[k]) for k in cur_k}

    daily = []
    if len(cur) > 0 and "TotalAmount" in cur.columns:
        daily_rev = cur.groupby(cur["InvoiceDate"].dt.date)["TotalAmount"].sum()
        for d, v in daily_rev.items():
            daily.append({"date": d.strftime("%Y-%m-%d"), "revenue": float(v)})

    return {
        "current_period": {"start": current_start.strftime("%Y-%m-%d"), "end": end.strftime("%Y-%m-%d"), **cur_k},
        "prior_period": {"start": prior_start.strftime("%Y-%m-%d"), "end": prior_end.strftime("%Y-%m-%d"), **prior_k},
        "deltas_pct": deltas,
        "daily_revenue": daily,
        "period_days": period_days,
    }


# ---------- Cohort retention ----------

def compute_cohort_retention(df, max_periods=12):
    if df is None or "CustomerID" not in df.columns or "InvoiceDate" not in df.columns:
        if "Year" in df.columns and "Month" in df.columns:
            df = df.copy()
            df["InvoiceDate"] = pd.to_datetime(dict(year=df["Year"], month=df["Month"], day=df.get("Day", 1)), errors="coerce")
        else:
            return {"error": "no date information"}

    df = df.copy()
    df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"], errors="coerce")
    df = df[df["InvoiceDate"].notna()]
    df = df[df["CustomerID"].astype(str).str.lower() != "unknown"]
    if len(df) == 0:
        return {"error": "no valid customer or date data"}

    df["order_period"] = df["InvoiceDate"].dt.to_period("M")
    cohorts = df.groupby("CustomerID")["order_period"].min().rename("cohort")
    df = df.join(cohorts, on="CustomerID")
    df["period_index"] = (df["order_period"] - df["cohort"]).apply(lambda x: x.n if hasattr(x, "n") else 0)
    df = df[df["period_index"] < max_periods]

    cohort_table = df.groupby(["cohort", "period_index"])["CustomerID"].nunique().unstack(fill_value=0)
    if cohort_table.empty:
        return {"cohorts": [], "max_periods": max_periods}
    cohort_sizes = cohort_table.iloc[:, 0]
    retention = cohort_table.divide(cohort_sizes, axis=0).round(3) * 100

    cohort_list = []
    for cohort_period, row in retention.iterrows():
        cohort_list.append({
            "cohort": str(cohort_period),
            "size": int(cohort_sizes[cohort_period]),
            "retention": [round(float(v), 1) for v in row.values],
        })
    return {"cohorts": cohort_list, "max_periods": max_periods}


# ---------- Bundle simulator ----------

def simulate_bundle(df, products, discount_pct=10.0):
    """Given a proposed bundle (list of product names) and a discount %,
    estimate: current co-purchase rate, projected lift in attach rate (assumes
    bundling halves the friction to buy together), and revenue impact."""
    if df is None or not products or len(products) < 2:
        return {"error": "Provide at least 2 products"}
    if "InvoiceNo" not in df.columns:
        return {"error": "missing InvoiceNo column"}

    invoices_by_product = {p: set(df[df["Description"] == p]["InvoiceNo"].unique()) for p in products}
    sizes = {p: len(inv) for p, inv in invoices_by_product.items()}
    if any(v == 0 for v in sizes.values()):
        return {"error": "One or more products not found in data", "products": products, "sizes": sizes}

    total_tx = df["InvoiceNo"].nunique()
    all_together = set.intersection(*invoices_by_product.values())
    any_member = set.union(*invoices_by_product.values())
    current_attach = len(all_together) / total_tx if total_tx else 0

    # Project: bundling typically reduces friction. Optimistic model assumes
    # 30% of single-buyers (those who bought one but not all) convert to full bundle.
    single_only = any_member - all_together
    expected_lift_factor = 0.30
    projected_extra_baskets = int(len(single_only) * expected_lift_factor)
    projected_total_bundles = len(all_together) + projected_extra_baskets

    avg_bundle_price = 0
    if "UnitPrice" in df.columns:
        avg_bundle_price = float(
            sum(df[df["Description"] == p]["UnitPrice"].mean() or 0 for p in products)
        )
    discounted_price = avg_bundle_price * (1 - discount_pct / 100)

    current_bundle_revenue = float(df[df["InvoiceNo"].isin(all_together)]["TotalAmount"].sum()) if "TotalAmount" in df.columns else 0
    projected_revenue = projected_total_bundles * discounted_price
    revenue_delta = projected_revenue - current_bundle_revenue

    return {
        "products": products,
        "discount_pct": discount_pct,
        "current": {
            "co_purchase_baskets": len(all_together),
            "co_purchase_rate": round(current_attach * 100, 2),
            "any_member_baskets": len(any_member),
            "estimated_bundle_revenue": round(current_bundle_revenue, 2),
        },
        "projected": {
            "extra_bundle_baskets": projected_extra_baskets,
            "total_bundle_baskets": projected_total_bundles,
            "lift_factor": expected_lift_factor,
            "discounted_bundle_price": round(discounted_price, 2),
            "projected_bundle_revenue": round(projected_revenue, 2),
            "revenue_delta": round(revenue_delta, 2),
        },
        "assumptions": [
            f"{int(expected_lift_factor * 100)}% of single-product buyers convert to full bundle",
            f"Discount of {discount_pct}% applied to sum of product avg prices",
        ],
    }

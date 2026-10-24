"""Analytics aggregation logic originally written for the single-store prototype."""
from datetime import datetime

import pandas as pd

MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
WEEKDAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def compute_summary(df):
    if df is None or len(df) == 0:
        return {"error": "no data"}
    total_revenue = float(df["TotalAmount"].sum()) if "TotalAmount" in df.columns else 0.0
    total_transactions = int(df["InvoiceNo"].nunique()) if "InvoiceNo" in df.columns else 0
    total_records = len(df)
    avg_transaction = total_revenue / total_transactions if total_transactions else 0

    multi_count = 0
    multi_pct = 0
    if "InvoiceNo" in df.columns:
        sizes = df.groupby("InvoiceNo").size()
        multi_count = int((sizes > 1).sum())
        multi_pct = (multi_count / total_transactions * 100) if total_transactions else 0

    avg_basket = 0.0
    median_basket = 0.0
    if "InvoiceNo" in df.columns and "Quantity" in df.columns:
        baskets = df.groupby("InvoiceNo")["Quantity"].sum()
        avg_basket = float(baskets.mean()) if not baskets.empty else 0
        median_basket = float(baskets.median()) if not baskets.empty else 0

    top10_pct = 0
    if "Description" in df.columns:
        pc = df["Description"].value_counts()
        top10_pct = (pc.head(10).sum() / pc.sum() * 100) if pc.sum() else 0

    critical_cols = ["InvoiceNo", "Description", "Quantity", "UnitPrice", "CustomerID", "Country"]
    missing = {}
    for c in critical_cols:
        missing[c] = int(df[c].isnull().sum()) if c in df.columns else total_records
    total_cells = total_records * len(critical_cols)
    completeness = round((1 - sum(missing.values()) / total_cells) * 100, 2) if total_cells else 0

    date_range = {"start": "Unknown", "end": "Unknown", "days": 0}
    if "InvoiceDate" in df.columns:
        try:
            inv = pd.to_datetime(df["InvoiceDate"], errors="coerce")
            if inv.notna().any():
                date_range = {
                    "start": inv.min().strftime("%Y-%m-%d"),
                    "end": inv.max().strftime("%Y-%m-%d"),
                    "days": int((inv.max() - inv.min()).days),
                }
        except Exception:
            pass
    elif "Year" in df.columns:
        miny, maxy = int(df["Year"].min()), int(df["Year"].max())
        date_range = {"start": f"{miny}-01-01", "end": f"{maxy}-12-31", "years": maxy - miny + 1}

    return {
        "total_transactions": total_transactions,
        "total_products": int(df["Description"].nunique()) if "Description" in df.columns else 0,
        "total_customers": int(df["CustomerID"].nunique()) if "CustomerID" in df.columns else 0,
        "total_revenue": total_revenue,
        "avg_transaction_value": round(avg_transaction, 2),
        "total_countries": int(df["Country"].nunique()) if "Country" in df.columns else 0,
        "multi_item_percentage": round(multi_pct, 1),
        "avg_basket_size": round(avg_basket, 2),
        "median_basket_size": round(median_basket, 2),
        "top_10_products_percentage": round(top10_pct, 1),
        "date_range": date_range,
        "data_quality": {
            "total_records": total_records,
            "data_completeness": completeness,
            "missing_customers": missing.get("CustomerID", 0),
            "missing_descriptions": missing.get("Description", 0),
            "missing_prices": missing.get("UnitPrice", 0),
            "missing_quantities": missing.get("Quantity", 0),
            "unique_products": int(df["Description"].nunique()) if "Description" in df.columns else 0,
            "unique_customers": int(df["CustomerID"].nunique()) if "CustomerID" in df.columns else 0,
            "revenue_per_transaction": round(avg_transaction, 2),
            "multi_item_transactions": multi_count,
        },
    }


def compute_seasonal(df):
    if df is None:
        return {"monthly_data": [], "hourly_data": [], "weekday_data": []}
    monthly, hourly, weekday = [], [], []
    global_rev = float(df["TotalAmount"].sum()) if "TotalAmount" in df.columns else 0

    if "Month" in df.columns and "TotalAmount" in df.columns:
        stats = df.groupby("Month").agg({"TotalAmount": ["sum", "mean", "count"], "InvoiceNo": "nunique", "CustomerID": "nunique", "Description": "nunique"}).round(2).reset_index()
        stats.columns = ["Month", "total_revenue", "avg_revenue", "record_count", "transaction_count", "customer_count", "product_variety"]
        for _, row in stats.iterrows():
            mdf = df[df["Month"] == row["Month"]]
            tx_values = mdf.groupby("InvoiceNo")["TotalAmount"].sum() if "InvoiceNo" in mdf.columns else pd.Series(dtype=float)
            monthly.append({
                "month": int(row["Month"]),
                "month_name": MONTH_NAMES[int(row["Month"]) - 1] if 1 <= int(row["Month"]) <= 12 else "Unknown",
                "revenue": float(row["total_revenue"]),
                "transactions": int(row["transaction_count"]),
                "customers": int(row["customer_count"]),
                "product_variety": int(row["product_variety"]),
                "avg_transaction": float(tx_values.mean()) if not tx_values.empty else 0,
                "median_transaction": float(tx_values.median()) if not tx_values.empty else 0,
                "records": int(row["record_count"]),
                "revenue_share": round(row["total_revenue"] / global_rev * 100, 2) if global_rev else 0,
            })

    if "Hour" in df.columns and "TotalAmount" in df.columns:
        stats = df.groupby("Hour").agg({"TotalAmount": ["sum", "mean", "count"], "InvoiceNo": "nunique"}).round(2).reset_index()
        stats.columns = ["Hour", "total_revenue", "avg_revenue", "record_count", "transaction_count"]
        for _, row in stats.iterrows():
            h = int(row["Hour"])
            hourly.append({
                "hour": h,
                "revenue": float(row["total_revenue"]),
                "transactions": int(row["transaction_count"]),
                "records": int(row["record_count"]),
                "avg_transaction": float(row["avg_revenue"]),
                "time_period": "Morning" if 6 <= h < 12 else "Afternoon" if 12 <= h < 18 else "Evening" if 18 <= h < 24 else "Night",
            })

    if "Weekday" in df.columns and "TotalAmount" in df.columns:
        stats = df.groupby("Weekday").agg({"TotalAmount": ["sum", "mean", "count"], "InvoiceNo": "nunique", "CustomerID": "nunique"}).round(2).reset_index()
        stats.columns = ["Weekday", "total_revenue", "avg_revenue", "record_count", "transaction_count", "customer_count"]
        stats["Weekday"] = pd.Categorical(stats["Weekday"], categories=WEEKDAY_ORDER, ordered=True)
        stats = stats.sort_values("Weekday")
        for _, row in stats.iterrows():
            wdf = df[df["Weekday"] == row["Weekday"]]
            tx_values = wdf.groupby("InvoiceNo")["TotalAmount"].sum() if "InvoiceNo" in wdf.columns else pd.Series(dtype=float)
            weekday.append({
                "weekday": str(row["Weekday"]),
                "weekday_num": WEEKDAY_ORDER.index(str(row["Weekday"])) if str(row["Weekday"]) in WEEKDAY_ORDER else 0,
                "revenue": float(row["total_revenue"]),
                "transactions": int(row["transaction_count"]),
                "customers": int(row["customer_count"]),
                "records": int(row["record_count"]),
                "avg_transaction": float(tx_values.mean()) if not tx_values.empty else 0,
                "revenue_per_customer": float(row["total_revenue"] / row["customer_count"]) if row["customer_count"] else 0,
            })

    peak_month = max(monthly, key=lambda x: x["revenue"])["month_name"] if monthly else None
    peak_hour = max(hourly, key=lambda x: x["revenue"])["hour"] if hourly else None
    peak_weekday = max(weekday, key=lambda x: x["revenue"])["weekday"] if weekday else None

    return {
        "monthly_data": monthly,
        "hourly_data": hourly,
        "weekday_data": weekday,
        "metadata": {
            "total_months": len(monthly),
            "total_hours": len(hourly),
            "total_weekdays": len(weekday),
            "peak_month": peak_month,
            "peak_hour": peak_hour,
            "peak_weekday": peak_weekday,
            "global_total_revenue": global_rev,
        },
    }


def compute_seasonal_product(df, product_name=None, year=None, month=None):
    filtered = df.copy()
    if year and year != "all" and "Year" in filtered.columns:
        try:
            filtered = filtered[filtered["Year"] == int(year)]
        except ValueError:
            pass
    if month and month != "all" and "Month" in filtered.columns:
        try:
            filtered = filtered[filtered["Month"] == int(month)]
        except ValueError:
            pass
    if product_name and product_name != "all":
        filtered = filtered[filtered["Description"].astype(str).str.lower().str.contains(product_name.lower(), na=False)]

    if len(filtered) == 0:
        return {"monthly_data": [], "hourly_data": [], "weekday_data": [], "top_products": [], "metadata": {"total_records": 0, "total_revenue": 0}}

    monthly = []
    if "Month" in filtered.columns and "TotalAmount" in filtered.columns:
        s = filtered.groupby("Month").agg({"TotalAmount": "sum", "InvoiceNo": "nunique", "Description": "nunique", "Quantity": "sum"}).reset_index()
        for _, row in s.iterrows():
            mn = int(row["Month"])
            monthly.append({"month": mn, "month_name": MONTH_NAMES[mn - 1] if 1 <= mn <= 12 else "Unknown", "revenue": float(row["TotalAmount"]), "transactions": int(row["InvoiceNo"]), "products": int(row["Description"]), "quantity": int(row["Quantity"])})

    hourly = []
    if "Hour" in filtered.columns and "TotalAmount" in filtered.columns:
        s = filtered.groupby("Hour").agg({"TotalAmount": "sum", "InvoiceNo": "nunique", "Quantity": "sum"}).reset_index()
        for _, row in s.iterrows():
            h = int(row["Hour"])
            hourly.append({"hour": h, "revenue": float(row["TotalAmount"]), "transactions": int(row["InvoiceNo"]), "quantity": int(row["Quantity"]), "time_period": "Morning" if 6 <= h < 12 else "Afternoon" if 12 <= h < 18 else "Evening" if 18 <= h < 24 else "Night"})

    weekday = []
    if "Weekday" in filtered.columns and "TotalAmount" in filtered.columns:
        s = filtered.groupby("Weekday").agg({"TotalAmount": "sum", "InvoiceNo": "nunique", "Quantity": "sum"}).reset_index()
        s["Weekday"] = pd.Categorical(s["Weekday"], categories=WEEKDAY_ORDER, ordered=True)
        s = s.sort_values("Weekday")
        for _, row in s.iterrows():
            weekday.append({"weekday": str(row["Weekday"]), "revenue": float(row["TotalAmount"]), "transactions": int(row["InvoiceNo"]), "quantity": int(row["Quantity"])})

    if not product_name or product_name == "all":
        top_products = filtered["Description"].value_counts().head(10).index.tolist()
    else:
        invoices = filtered[filtered["Description"].astype(str).str.lower().str.contains(product_name.lower(), na=False)]["InvoiceNo"].unique()
        top_products = filtered[filtered["InvoiceNo"].isin(invoices)]["Description"].value_counts().head(10).index.tolist()

    return {
        "monthly_data": monthly,
        "hourly_data": hourly,
        "weekday_data": weekday,
        "top_products": top_products[:5],
        "metadata": {
            "total_records": int(len(filtered)),
            "total_revenue": float(filtered["TotalAmount"].sum()) if "TotalAmount" in filtered.columns else 0,
            "product_filter": product_name or "None",
            "year_filter": year or "all",
            "month_filter": month or "all",
        },
    }


def compute_revenue_by_country(df, country=None, year=None, limit=10):
    filtered = df.copy()
    if country and country != "all" and "Country" in filtered.columns:
        filtered = filtered[filtered["Country"] == country]
    if year and year != "all" and "Year" in filtered.columns:
        try:
            filtered = filtered[filtered["Year"] == int(year)]
        except ValueError:
            pass
    if len(filtered) == 0 or "Country" not in filtered.columns:
        return {"revenue_analysis": [], "metadata": {"total_countries": 0, "global_total_revenue": 0, "filters_applied": {"country": country, "year": year}}}

    if "CustomerID" in filtered.columns:
        agg = {"TotalAmount": ["sum", "mean"], "InvoiceNo": "nunique", "CustomerID": "nunique", "Quantity": "sum"}
        cols = ["Country", "total_revenue", "avg_revenue", "transaction_count", "customer_count", "total_quantity"]
    else:
        agg = {"TotalAmount": ["sum", "mean"], "InvoiceNo": "nunique", "Quantity": "sum"}
        cols = ["Country", "total_revenue", "avg_revenue", "transaction_count", "total_quantity"]

    stats = filtered.groupby("Country").agg(agg).reset_index()
    stats.columns = cols
    if "customer_count" not in stats.columns:
        stats["customer_count"] = 0
    stats = stats.sort_values("total_revenue", ascending=False)
    global_total = float(filtered["TotalAmount"].sum())

    out = []
    for _, row in stats.head(limit).iterrows():
        market_share = (row["total_revenue"] / global_total * 100) if global_total else 0
        rev_per_cust = row["total_revenue"] / row["customer_count"] if row["customer_count"] else 0
        avg_tx = row["total_revenue"] / row["transaction_count"] if row["transaction_count"] else 0
        out.append({
            "country": str(row["Country"]),
            "total_revenue": float(row["total_revenue"]),
            "transaction_count": int(row["transaction_count"]),
            "customer_count": int(row["customer_count"]),
            "total_quantity": int(row["total_quantity"]),
            "market_share": float(market_share),
            "revenue_per_customer": float(rev_per_cust),
            "avg_transaction_value": float(avg_tx),
            "avg_revenue": float(row["avg_revenue"]),
        })
    return {
        "revenue_analysis": out,
        "metadata": {
            "total_countries": len(stats),
            "global_total_revenue": global_total,
            "global_avg_transaction": float(filtered.groupby("InvoiceNo")["TotalAmount"].sum().mean()) if "InvoiceNo" in filtered.columns else 0,
            "filters_applied": {"country": country, "year": year},
        },
    }


def compute_top_products(df, sort_by="revenue", limit=20):
    if "Description" not in df.columns or len(df) == 0:
        return {"products": [], "metadata": {"total_products_analyzed": 0}}

    stats = df.groupby("Description").agg({"TotalAmount": "sum", "InvoiceNo": "nunique", "Quantity": "sum"}).reset_index()
    stats.columns = ["Description", "total_revenue", "transaction_count", "total_quantity"]

    if "CustomerID" in df.columns:
        cc = df.groupby("Description")["CustomerID"].nunique().reset_index()
        cc.columns = ["Description", "customer_count"]
        stats = stats.merge(cc, on="Description", how="left")
        stats["customer_count"] = stats["customer_count"].fillna(0).astype(int)
    else:
        stats["customer_count"] = 0

    if "UnitPrice" in df.columns:
        ap = df.groupby("Description")["UnitPrice"].mean().reset_index()
        ap.columns = ["Description", "avg_price"]
        stats = stats.merge(ap, on="Description", how="left").fillna({"avg_price": 0})
    else:
        stats["avg_price"] = 0

    rec = df["Description"].value_counts().reset_index()
    rec.columns = ["Description", "record_count"]
    stats = stats.merge(rec, on="Description", how="left").fillna({"record_count": 0})

    stats["avg_quantity"] = (stats["total_quantity"] / stats["transaction_count"]).fillna(0)

    sort_map = {"revenue": "total_revenue", "transactions": "transaction_count", "customers": "customer_count", "quantity": "total_quantity"}
    sort_col = sort_map.get(sort_by, "total_revenue")
    stats = stats.sort_values(sort_col, ascending=False)

    total_rev = float(df["TotalAmount"].sum())
    total_tx = int(df["InvoiceNo"].nunique()) if "InvoiceNo" in df.columns else 0
    total_cust = int(df["CustomerID"].nunique()) if "CustomerID" in df.columns else 0

    products = []
    for _, row in stats.head(limit).iterrows():
        pdf = df[df["Description"] == row["Description"]]
        return_rate = 0
        if "CustomerID" in pdf.columns and row["customer_count"] > 0:
            cust = pdf.groupby("CustomerID").size()
            return_rate = len(cust[cust > 1]) / row["customer_count"] * 100
        peak_hour = 12
        if "Hour" in pdf.columns:
            mode = pdf["Hour"].mode()
            if not mode.empty:
                peak_hour = int(mode.iloc[0])
        products.append({
            "rank": len(products) + 1,
            "description": str(row["Description"]),
            "total_revenue": float(row["total_revenue"]),
            "revenue_share": round((row["total_revenue"] / total_rev * 100) if total_rev else 0, 2),
            "transactions": int(row["transaction_count"]),
            "transaction_share": round((row["transaction_count"] / total_tx * 100) if total_tx else 0, 2),
            "customers": int(row["customer_count"]),
            "customer_share": round((row["customer_count"] / total_cust * 100) if total_cust else 0, 2),
            "avg_price": float(row["avg_price"]),
            "avg_quantity": float(row["avg_quantity"]),
            "total_quantity": int(row["total_quantity"]),
            "records": int(row["record_count"]),
            "return_customer_rate": round(float(return_rate), 1),
            "peak_hour": peak_hour,
            "revenue_per_transaction": float(row["total_revenue"] / row["transaction_count"]) if row["transaction_count"] else 0,
            "revenue_per_customer": float(row["total_revenue"] / row["customer_count"]) if row["customer_count"] else 0,
        })

    return {
        "products": products,
        "metadata": {
            "total_products_analyzed": int(len(stats)),
            "sort_by": sort_by,
            "filtered_records": int(len(df)),
            "total_revenue": total_rev,
            "total_transactions": total_tx,
            "total_customers": total_cust,
        },
    }


def compute_filters(df):
    filters = {"countries": [], "years": [], "months": [], "hours": [], "products": [], "weekdays": []}
    if df is None or len(df) == 0:
        return filters

    if "Country" in df.columns:
        filters["countries"] = sorted([str(c).strip() for c in df["Country"].dropna().unique() if c and str(c).strip().lower() != "unknown"])
    if "Year" in df.columns:
        filters["years"] = sorted([int(y) for y in df["Year"].dropna().unique()])
    if "Month" in df.columns:
        months = sorted([int(m) for m in df["Month"].dropna().unique() if 1 <= m <= 12])
        filters["months"] = [{"value": m, "name": MONTH_NAMES[m - 1]} for m in months]
    if "Hour" in df.columns:
        hours = sorted([int(h) for h in df["Hour"].dropna().unique() if 0 <= h <= 23])
        filters["hours"] = [{"value": h, "name": f"{h:02d}:00"} for h in hours]
    if "Description" in df.columns:
        top = df["Description"].value_counts().head(100).index.tolist()
        seen, cleaned = set(), []
        for p in top:
            if isinstance(p, str):
                cp = p.strip()
                if cp and cp not in seen:
                    seen.add(cp)
                    cleaned.append(cp)
        filters["products"] = sorted(cleaned)[:100]
    if "Weekday" in df.columns:
        present = sorted([str(w).strip() for w in df["Weekday"].dropna().unique() if w and str(w).strip()])
        filters["weekdays"] = sorted(present, key=lambda x: WEEKDAY_ORDER.index(x) if x in WEEKDAY_ORDER else 99)

    filters["statistics"] = {
        "total_countries": len(filters["countries"]),
        "total_years": len(filters["years"]),
        "total_months": len(filters["months"]),
        "total_products": len(filters["products"]),
        "data_range": {
            "min_year": min(filters["years"]) if filters["years"] else None,
            "max_year": max(filters["years"]) if filters["years"] else None,
        },
    }
    return filters


def compute_product_detail(df_filtered, product_name):
    if not product_name:
        return None
    if product_name in df_filtered["Description"].values:
        exact = product_name
    else:
        sim = df_filtered[df_filtered["Description"].astype(str).str.lower().str.contains(product_name.lower(), na=False)]["Description"].unique()
        if len(sim) == 0:
            return None
        exact = sim[0]

    product_df = df_filtered[df_filtered["Description"] == exact]
    if len(product_df) == 0:
        return None

    from app.services.mba_service import calculate_product_stats
    stats = calculate_product_stats(exact, df_filtered)

    monthly_trend = []
    if "Month" in product_df.columns and "Year" in product_df.columns:
        mt = product_df.groupby(["Year", "Month"]).agg({"TotalAmount": "sum", "Quantity": "sum", "InvoiceNo": "nunique"}).reset_index()
        for _, row in mt.iterrows():
            monthly_trend.append({"year": int(row["Year"]), "month": int(row["Month"]), "revenue": float(row["TotalAmount"]), "quantity": int(row["Quantity"]), "transactions": int(row["InvoiceNo"])})

    associated = []
    if "InvoiceNo" in product_df.columns:
        invoices = set(product_df["InvoiceNo"].unique())
        if invoices:
            co = df_filtered[df_filtered["InvoiceNo"].isin(invoices)]
            counts = co[co["Description"] != exact]["Description"].value_counts().head(10)
            for prod, n in counts.items():
                associated.append({"product": prod, "co_purchase_count": int(n), "co_occurrence_rate": round(n / len(invoices) * 100, 1)})

    top_customers = []
    if "CustomerID" in product_df.columns:
        cs = product_df.groupby("CustomerID").agg({"TotalAmount": "sum", "Quantity": "sum", "InvoiceNo": "nunique"}).reset_index()
        for _, row in cs.nlargest(5, "TotalAmount").iterrows():
            top_customers.append({"customer_id": row["CustomerID"], "total_spent": float(row["TotalAmount"]), "total_quantity": int(row["Quantity"]), "purchases": int(row["InvoiceNo"])})

    time_period = "Unknown"
    if "Year" in df_filtered.columns:
        time_period = f"{int(df_filtered['Year'].min())} - {int(df_filtered['Year'].max())}"

    return {
        "name": exact,
        "statistics": stats,
        "monthly_trend": monthly_trend,
        "associated_products": associated,
        "top_customers": top_customers,
        "metadata": {
            "analysis_date": datetime.utcnow().isoformat(),
            "records_analyzed": int(len(product_df)),
            "time_period_covered": time_period,
        },
    }

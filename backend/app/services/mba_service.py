"""Market Basket Analysis logic originally written for the single-store prototype."""
import time
import pandas as pd
from mlxtend.frequent_patterns import apriori, association_rules


def remove_duplicate_rules(rules_df):
    if len(rules_df) == 0:
        return rules_df
    rules_dict = {}
    for _, rule in rules_df.iterrows():
        antecedents = frozenset(rule["antecedents"])
        consequents = frozenset(rule["consequents"])
        key1 = (antecedents, consequents)
        key2 = (consequents, antecedents)
        if key1 in rules_dict:
            if rule["confidence"] > rules_dict[key1]["confidence"]:
                rules_dict[key1] = rule
        elif key2 in rules_dict:
            if rule["confidence"] > rules_dict[key2]["confidence"]:
                rules_dict[key2] = rule
        else:
            rules_dict[key1] = rule
    return pd.DataFrame(list(rules_dict.values()))


def _build_basket(df_top):
    basket = (
        df_top.groupby(["InvoiceNo", "Description"])["Quantity"]
        .sum()
        .unstack(fill_value=0)
        .reset_index()
        .set_index("InvoiceNo")
    )
    basket_sets = (basket > 0).astype(int)
    column_sums = basket_sets.sum()
    columns_to_keep = column_sums[column_sums >= 3].index.tolist()
    basket_sets = basket_sets[columns_to_keep]
    return basket_sets


def compute_association_rules(df, min_support=0.01, min_confidence=0.3, min_lift=1.0, limit=50, simple=True):
    start = time.time()
    if df is None or len(df) < 100:
        return {"success": True, "data": [], "message": "Insufficient data for analysis.", "metadata": {"processing_time": round(time.time() - start, 2)}}

    top_products = df["Description"].value_counts().head(100).index.tolist()
    df_top = df[df["Description"].isin(top_products)]
    if len(df_top) < 50:
        return {"success": True, "data": [], "message": "Not enough transactions.", "metadata": {"processing_time": round(time.time() - start, 2)}}

    basket_sets = _build_basket(df_top)
    if len(basket_sets.columns) < 2:
        return {"success": True, "data": [], "message": "No product associations found.", "metadata": {"processing_time": round(time.time() - start, 2)}}

    frequent = apriori(basket_sets, min_support=min_support, use_colnames=True, max_len=2, low_memory=True, verbose=0)
    if len(frequent) == 0:
        adjusted = max(0.0005, min_support / 2)
        frequent = apriori(basket_sets, min_support=adjusted, use_colnames=True, max_len=2, low_memory=True, verbose=0)
        min_support = adjusted
    if len(frequent) == 0:
        return {"success": True, "data": [], "message": "No frequent patterns found.", "metadata": {"processing_time": round(time.time() - start, 2)}}

    rules = association_rules(frequent, metric="confidence", min_threshold=min_confidence)
    rules = rules[rules["lift"] >= min_lift]
    if len(rules) == 0:
        return {"success": True, "data": [], "message": "No significant rules found.", "metadata": {"processing_time": round(time.time() - start, 2)}}

    rules = rules.sort_values(["confidence", "lift"], ascending=False)
    rules = remove_duplicate_rules(rules)
    rules = rules.sort_values(["confidence", "lift"], ascending=False).reset_index(drop=True)

    formatted = []
    for _, rule in rules.head(limit).iterrows():
        antecedents = list(rule["antecedents"])
        consequents = list(rule["consequents"])
        if not antecedents or not consequents:
            continue
        a = next(iter(antecedents))
        c = next(iter(consequents))
        item = {
            "rule": f"{a} → {c}",
            "antecedent": a,
            "consequent": c,
            "confidence": round(float(rule["confidence"]), 3),
            "lift": round(float(rule["lift"]), 3),
            "support": round(float(rule["support"]), 4),
            "antecedent_support": round(float(rule["antecedent support"]), 4),
            "consequent_support": round(float(rule["consequent support"]), 4),
            "leverage": round(float(rule["leverage"]), 4),
            "conviction": round(float(rule["conviction"]), 3) if not pd.isna(rule["conviction"]) else None,
        }
        if not simple:
            item["antecedents"] = antecedents
            item["consequents"] = consequents
        formatted.append(item)

    return {
        "success": True,
        "data": formatted,
        "metadata": {
            "total_rules_found": len(rules),
            "rules_returned": len(formatted),
            "processing_time": round(time.time() - start, 2),
            "parameters": {"min_support": min_support, "min_confidence": min_confidence, "min_lift": min_lift, "limit": limit},
            "filter_stats": {"products_in_analysis": len(basket_sets.columns), "transactions_in_analysis": len(basket_sets)},
        },
    }


def compute_product_bundles(df, min_support=0.01, min_confidence=0.3, min_lift=1.0, limit=50, filters_applied=None):
    start = time.time()
    if df is None or len(df) < 100:
        return {"success": True, "bundles": [], "message": "Insufficient data.", "metadata": {"processing_time": round(time.time() - start, 2)}}
    top_products = df["Description"].value_counts().head(100).index.tolist()
    df_top = df[df["Description"].isin(top_products)]
    if len(df_top) < 50:
        return {"success": True, "bundles": [], "message": "Not enough data.", "metadata": {"processing_time": round(time.time() - start, 2)}}
    basket_sets = _build_basket(df_top)
    if len(basket_sets.columns) < 2:
        return {"success": True, "bundles": [], "message": "Insufficient products.", "metadata": {"processing_time": round(time.time() - start, 2)}}
    frequent = apriori(basket_sets, min_support=min_support, use_colnames=True, max_len=2, low_memory=True, verbose=0)
    if len(frequent) == 0:
        adjusted = max(0.0005, min_support / 2)
        frequent = apriori(basket_sets, min_support=adjusted, use_colnames=True, max_len=2, low_memory=True, verbose=0)
        min_support = adjusted
    if len(frequent) == 0:
        return {"success": True, "bundles": [], "message": "No product associations.", "metadata": {"processing_time": round(time.time() - start, 2)}}
    rules = association_rules(frequent, metric="confidence", min_threshold=min_confidence)
    rules = rules[rules["lift"] >= min_lift]
    if len(rules) == 0:
        return {"success": True, "bundles": [], "message": "No strong bundles.", "metadata": {"processing_time": round(time.time() - start, 2)}}
    rules = rules.sort_values(["confidence", "lift"], ascending=False)
    rules = remove_duplicate_rules(rules)
    rules = rules.sort_values(["confidence", "lift"], ascending=False).reset_index(drop=True)

    bundles = []
    total_tx = len(basket_sets)
    for _, rule in rules.head(limit).iterrows():
        antecedents = list(rule["antecedents"])
        consequents = list(rule["consequents"])
        if not antecedents or not consequents:
            continue
        a = next(iter(antecedents))
        c = next(iter(consequents))
        bundles.append({
            "bundle_id": f"B{len(bundles)+1:03d}",
            "products": [a, c],
            "bundle_name": f"{a[:30]} & {c[:30]}",
            "confidence": round(float(rule["confidence"]), 3),
            "lift": round(float(rule["lift"]), 2),
            "transaction_count": int(rule["support"] * total_tx),
            "support": round(float(rule["support"]), 4),
            "antecedent": a,
            "consequent": c,
            "antecedent_support": round(float(rule["antecedent support"]), 4),
            "consequent_support": round(float(rule["consequent support"]), 4),
        })
    return {
        "success": True,
        "bundles": bundles,
        "total_bundles_found": len(bundles),
        "metadata": {
            "processing_time": round(time.time() - start, 2),
            "parameters": {"min_support": min_support, "min_confidence": min_confidence, "min_lift": min_lift, "limit": limit},
            "filter_stats": {"products_in_analysis": len(basket_sets.columns), "transactions_in_analysis": len(basket_sets)},
            "filters_applied": filters_applied or {},
        },
    }


def compute_network_graph(df, min_support=0.02, limit=20):
    if df is None or "Description" not in df.columns:
        return {"success": True, "network": {"nodes": [], "links": []}, "metadata": {"nodes_count": 0, "links_count": 0}}
    if "TotalAmount" in df.columns and "InvoiceNo" in df.columns:
        product_stats = df.groupby("Description").agg({"TotalAmount": "sum", "InvoiceNo": "nunique"}).reset_index()
        product_stats.columns = ["Description", "total_revenue", "transaction_count"]
        top_products = product_stats.nlargest(limit, "transaction_count")["Description"].tolist()
    else:
        top_products = df["Description"].value_counts().head(limit).index.tolist()

    nodes = []
    invoices_by_product = {}
    for i, product in enumerate(top_products):
        product_df = df[df["Description"] == product]
        revenue = float(product_df["TotalAmount"].sum()) if "TotalAmount" in product_df.columns else 0.0
        tx = int(product_df["InvoiceNo"].nunique()) if "InvoiceNo" in product_df.columns else len(product_df)
        customers = int(product_df["CustomerID"].nunique()) if "CustomerID" in product_df.columns else 0
        avg_price = 0.0
        if "UnitPrice" in product_df.columns:
            avg_price = float(product_df["UnitPrice"].mean() or 0)
        category = "Low Price" if avg_price < 10 else ("Medium Price" if avg_price < 50 else "High Price")
        invoices_by_product[product] = set(product_df["InvoiceNo"].unique()) if "InvoiceNo" in product_df.columns else set()
        nodes.append({
            "id": f"P{i:03d}",
            "name": product[:30],
            "full_name": product,
            "group": category,
            "value": float(revenue / 1000) if revenue > 0 else 1.0,
            "revenue": revenue,
            "transactions": tx,
            "customers": customers,
            "avg_price": avg_price,
            "degree": 0,
        })

    total_tx = df["InvoiceNo"].nunique() if "InvoiceNo" in df.columns else 1
    links = []
    link_id = 0
    for i, node_a in enumerate(nodes):
        inv_a = invoices_by_product.get(node_a["full_name"], set())
        for j in range(i + 1, min(i + 10, len(nodes))):
            node_b = nodes[j]
            inv_b = invoices_by_product.get(node_b["full_name"], set())
            common = inv_a & inv_b
            if len(common) >= 2:
                union = inv_a | inv_b
                jaccard = len(common) / len(union) if union else 0
                expected = (len(inv_a) * len(inv_b)) / total_tx if total_tx else 0
                lift = len(common) / expected if expected else 1.0
                if jaccard >= 0.01:
                    common_rev = float(df[df["InvoiceNo"].isin(common)]["TotalAmount"].sum()) if "TotalAmount" in df.columns else 0
                    links.append({
                        "id": f"L{link_id:04d}",
                        "source": node_a["id"],
                        "target": node_b["id"],
                        "source_name": node_a["name"],
                        "target_name": node_b["name"],
                        "value": float(jaccard),
                        "transactions": len(common),
                        "strength": float(lift),
                        "revenue": common_rev,
                    })
                    link_id += 1
                    node_a["degree"] += 1
                    node_b["degree"] += 1
    return {
        "success": True,
        "network": {"nodes": nodes, "links": links},
        "metadata": {
            "nodes_count": len(nodes),
            "links_count": len(links),
            "min_support": min_support,
            "avg_node_degree": sum(n["degree"] for n in nodes) / len(nodes) if nodes else 0,
            "max_node_degree": max((n["degree"] for n in nodes), default=0),
        },
    }


def calculate_product_stats(product_name, df_filtered):
    product_df = df_filtered[df_filtered["Description"].astype(str).str.lower() == product_name.lower()]
    if len(product_df) == 0:
        product_df = df_filtered[df_filtered["Description"].astype(str).str.lower().str.contains(product_name.lower(), na=False)]
    if len(product_df) == 0:
        return None
    stats = {
        "total_quantity": int(product_df["Quantity"].sum()) if "Quantity" in product_df.columns else 0,
        "total_revenue": float(product_df["TotalAmount"].sum()) if "TotalAmount" in product_df.columns else 0.0,
        "transaction_count": int(product_df["InvoiceNo"].nunique()) if "InvoiceNo" in product_df.columns else 0,
        "customer_count": int(product_df["CustomerID"].nunique()) if "CustomerID" in product_df.columns else 0,
        "avg_quantity_per_transaction": float(product_df.groupby("InvoiceNo")["Quantity"].sum().mean())
        if "InvoiceNo" in product_df.columns and "Quantity" in product_df.columns else 0.0,
        "peak_hour": int(product_df["Hour"].mode().iloc[0]) if "Hour" in product_df.columns and not product_df["Hour"].mode().empty else 12,
        "most_common_weekday": str(product_df["Weekday"].mode().iloc[0]) if "Weekday" in product_df.columns and not product_df["Weekday"].mode().empty else "Monday",
        "most_common_month": int(product_df["Month"].mode().iloc[0]) if "Month" in product_df.columns and not product_df["Month"].mode().empty else 1,
        "top_country": str(product_df["Country"].mode().iloc[0]) if "Country" in product_df.columns and not product_df["Country"].mode().empty else "Unknown",
    }
    if "UnitPrice" in product_df.columns:
        stats["avg_price"] = float(product_df["UnitPrice"].mean())
    elif stats["total_quantity"] > 0:
        stats["avg_price"] = stats["total_revenue"] / stats["total_quantity"]
    else:
        stats["avg_price"] = 0.0
    return stats

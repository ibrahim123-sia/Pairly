"""Column normalization helpers originally written for the single-store prototype."""

REQUIRED_COLUMNS = ["InvoiceNo", "Description", "Quantity", "UnitPrice"]
RECOMMENDED_COLUMNS = ["InvoiceDate", "CustomerID", "Country"]

ALIASES = {
    "InvoiceNo": ["invoice", "invoiceno", "invoicenumber", "transno", "transactionid", "transactionno", "order_id", "orderid"],
    "CustomerID": ["customerid", "customer", "customerno", "clientid", "client", "custid", "customer id", "customer_id"],
    "UnitPrice": ["unitprice", "price", "cost", "unitcost", "sellingprice", "unit_price"],
    "Description": ["description", "product", "productname", "product_name", "item", "itemname", "item_name"],
    "Quantity": ["quantity", "qty", "units", "unit", "count"],
    "InvoiceDate": ["invoicedate", "date", "orderdate", "order_date", "transactiondate", "transaction_date", "timestamp"],
    "Country": ["country", "region", "location"],
    "StockCode": ["stockcode", "stock_code", "sku", "productcode", "product_code"],
}


def map_column_names(df):
    """Rename DataFrame columns to canonical names based on common aliases."""
    df_mapped = df.copy()
    column_mapping = {}

    for canonical, aliases in ALIASES.items():
        if canonical in df_mapped.columns:
            continue
        for col in df_mapped.columns:
            if col.lower().strip().replace(" ", "_") in aliases or col.lower().strip() in aliases:
                column_mapping[col] = canonical
                break

    if column_mapping:
        df_mapped = df_mapped.rename(columns=column_mapping)
    return df_mapped, column_mapping


def validate_required_columns(df):
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    return missing

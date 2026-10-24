"""Filter helpers originally written for the single-store prototype."""


def apply_filters(df, filters):
    df_filtered = df.copy()

    country = filters.get("country")
    if country and country != "all" and "Country" in df_filtered.columns:
        if country.lower() != "unknown":
            df_filtered = df_filtered[df_filtered["Country"] == country]

    year = filters.get("year")
    if year and year != "all" and "Year" in df_filtered.columns:
        try:
            df_filtered = df_filtered[df_filtered["Year"] == int(year)]
        except (TypeError, ValueError):
            pass

    month = filters.get("month")
    if month and month != "all" and "Month" in df_filtered.columns:
        try:
            df_filtered = df_filtered[df_filtered["Month"] == int(month)]
        except (TypeError, ValueError):
            pass

    hour = filters.get("hour")
    if hour and hour != "all" and "Hour" in df_filtered.columns:
        try:
            df_filtered = df_filtered[df_filtered["Hour"] == int(hour)]
        except (TypeError, ValueError):
            pass

    product = filters.get("product")
    if product and product != "all" and "Description" in df_filtered.columns:
        needle = product.lower().strip()
        if needle:
            mask = df_filtered["Description"].astype(str).str.lower().str.contains(needle, na=False)
            df_filtered = df_filtered[mask]

    weekday = filters.get("weekday")
    if weekday and weekday != "all" and "Weekday" in df_filtered.columns:
        df_filtered = df_filtered[df_filtered["Weekday"] == weekday]

    return df_filtered


def extract_filters_from_args(args):
    return {
        "country": args.get("country"),
        "year": args.get("year"),
        "month": args.get("month"),
        "hour": args.get("hour"),
        "product": args.get("product"),
        "weekday": args.get("weekday"),
    }

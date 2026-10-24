"""Datetime feature extraction originally written for the single-store prototype."""
import pandas as pd

MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def extract_datetime_features(df):
    df_clean = df.copy()
    if "InvoiceDate" in df_clean.columns:
        df_clean["InvoiceDate"] = pd.to_datetime(df_clean["InvoiceDate"], errors="coerce")
        df_clean["Year"] = df_clean["InvoiceDate"].dt.year.fillna(2024).astype(int)
        df_clean["Month"] = df_clean["InvoiceDate"].dt.month.fillna(1).astype(int)
        df_clean["Day"] = df_clean["InvoiceDate"].dt.day.fillna(1).astype(int)
        df_clean["Hour"] = df_clean["InvoiceDate"].dt.hour.fillna(12).astype(int)
        df_clean["Weekday"] = df_clean["InvoiceDate"].dt.day_name().fillna("Monday")
        df_clean["Weekday_Num"] = df_clean["InvoiceDate"].dt.dayofweek.fillna(0).astype(int)
    elif "Year" in df_clean.columns and "Month" in df_clean.columns:
        df_clean["Year"] = pd.to_numeric(df_clean["Year"], errors="coerce").fillna(2024).astype(int)
        df_clean["Month"] = pd.to_numeric(df_clean["Month"], errors="coerce").fillna(1).astype(int)
        df_clean["Day"] = pd.to_numeric(df_clean.get("Day", 1), errors="coerce").fillna(1).astype(int)
        df_clean["Hour"] = pd.to_numeric(df_clean.get("Hour", 12), errors="coerce").fillna(12).astype(int)
        df_clean["Weekday"] = df_clean.get("Weekday", "Monday")
        df_clean["Weekday_Num"] = pd.to_numeric(df_clean.get("Weekday_Num", 0), errors="coerce").fillna(0).astype(int)
    else:
        df_clean["Year"] = 2010
        df_clean["Month"] = 1
        df_clean["Day"] = 1
        df_clean["Hour"] = 12
        df_clean["Weekday"] = "Monday"
        df_clean["Weekday_Num"] = 0

    df_clean["Month_Name"] = df_clean["Month"].apply(
        lambda x: MONTH_NAMES[x - 1] if 1 <= int(x) <= 12 else "Unknown"
    )
    return df_clean

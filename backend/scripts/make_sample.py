"""Build app/demo/sample_transactions.csv from a full cleaned export of the
UCI "Online Retail II" dataset (not stored in this repo).

The sample keeps whole invoices (so baskets stay intact) picked at random
across the full date range (so seasonal patterns survive). Columns that the
upload pipeline derives itself (TotalAmount, Year, Month, ...) are dropped.

Usage (from backend/):
    python scripts/make_sample.py --source path/to/Online_Retail_II_Cleaned.csv [--fraction 0.08] [--seed 42]
"""
import argparse
import os

import pandas as pd

BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DEFAULT_OUT = os.path.join(BACKEND, "app", "demo", "sample_transactions.csv")
KEEP = ["Invoice", "StockCode", "Description", "Quantity", "InvoiceDate", "Price", "CustomerID", "Country"]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source", required=True, help="full cleaned Online Retail II CSV")
    parser.add_argument("--out", default=DEFAULT_OUT)
    parser.add_argument("--fraction", type=float, default=0.08, help="share of invoices to keep")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    df = pd.read_csv(args.source, usecols=KEEP, dtype={"Invoice": str, "StockCode": str, "CustomerID": str})
    invoices = pd.Series(df["Invoice"].unique())
    keep = set(invoices.sample(frac=args.fraction, random_state=args.seed))
    sample = df[df["Invoice"].isin(keep)].copy()
    sample["InvoiceDate"] = pd.to_datetime(sample["InvoiceDate"], format="mixed").dt.strftime("%Y-%m-%d %H:%M")
    sample["CustomerID"] = sample["CustomerID"].str.replace(r"\.0$", "", regex=True)

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    sample.to_csv(args.out, index=False, lineterminator="\n")
    size_mb = os.path.getsize(args.out) / 1024 / 1024
    print(f"Wrote {len(sample):,} rows / {len(keep):,} invoices to {args.out} ({size_mb:.2f} MB)")


if __name__ == "__main__":
    main()

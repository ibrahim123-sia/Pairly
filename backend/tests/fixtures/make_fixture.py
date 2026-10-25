"""Write transactions_small.csv: a tiny, hand-designed basket dataset.

Two product pairs are planted so the expected association rules can be
worked out by hand (150 invoices in total):

  GREEN REGENCY TEACUP AND SAUCER  in invoices  0..39  (40 baskets)
  ROSES REGENCY TEACUP AND SAUCER  in invoices  4..48  (45 baskets)
      both: 4..39 = 36 baskets
      GREEN -> ROSES: support 36/150 = 0.24, confidence 36/40 = 0.9,
                      lift 0.9 / (45/150) = 3.0

  JUMBO BAG RED RETROSPOT          in invoices 60..109 (50 baskets)
  JUMBO BAG PINK POLKADOT          in invoices 86..115 (30 baskets)
      both: 86..109 = 24 baskets
      PINK -> RED:    support 24/150 = 0.16, confidence 24/30 = 0.8,
                      lift 0.8 / (50/150) = 2.4

Every invoice also has exactly one filler product (invoice % 6), spread
evenly, so fillers never form strong rules (their lift stays near 1).

Run from backend/:  python tests/fixtures/make_fixture.py
"""
import csv
import os
from datetime import datetime, timedelta

GREEN = "GREEN REGENCY TEACUP AND SAUCER"
ROSES = "ROSES REGENCY TEACUP AND SAUCER"
RED_BAG = "JUMBO BAG RED RETROSPOT"
PINK_BAG = "JUMBO BAG PINK POLKADOT"
FILLERS = [
    ("WHITE HANGING HEART T-LIGHT HOLDER", 2.55),
    ("PARTY BUNTING", 4.95),
    ("ASSORTED COLOUR BIRD ORNAMENT", 1.69),
    ("REGENCY CAKESTAND 3 TIER", 12.75),
    ("LUNCH BAG RED RETROSPOT", 1.65),
    ("SET OF 3 CAKE TINS PANTRY DESIGN", 4.95),
]
STOCK_CODES = {name: f"T{n:03d}" for n, name in enumerate([GREEN, ROSES, RED_BAG, PINK_BAG] + [f for f, _ in FILLERS])}
INVOICES = 150
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "transactions_small.csv")


def lines_for(i):
    items = []
    if 0 <= i <= 39:
        items.append((GREEN, 2, 2.95))
    if 4 <= i <= 48:
        items.append((ROSES, 2, 2.95))
    if 60 <= i <= 109:
        items.append((RED_BAG, 10, 1.95))
    if 86 <= i <= 115:
        items.append((PINK_BAG, 10, 1.95))
    name, price = FILLERS[i % len(FILLERS)]
    items.append((name, 1 + i % 4, price))
    return items


def main():
    start = datetime(2011, 1, 3, 9, 0)
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["Invoice", "StockCode", "Description", "Quantity", "InvoiceDate", "Price", "CustomerID", "Country"])
        rows = 0
        for i in range(INVOICES):
            when = start + timedelta(days=2 * i, hours=i % 8)
            for name, qty, price in lines_for(i):
                w.writerow([f"F{i:05d}", STOCK_CODES[name], name, qty, when.strftime("%Y-%m-%d %H:%M"), price,
                            13000 + i % 30, "France" if i % 10 == 0 else "United Kingdom"])
                rows += 1
    print(f"Wrote {rows} rows / {INVOICES} invoices to {OUT}")


if __name__ == "__main__":
    main()

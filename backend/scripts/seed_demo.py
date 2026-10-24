"""Create the Pairly demo store and demo manager, and load the sample dataset.

Run from backend/:
    python scripts/seed_demo.py                       # uses data/sample/online_retail_ii_sample.csv
    python scripts/seed_demo.py --file ../data/raw/Online_Retail_II_Cleaned.csv
    python scripts/seed_demo.py --reload              # load the file again even if data exists

Safe to run more than once.
"""
import argparse
import logging
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import get_config  # noqa: E402
from app.database import Base, SessionLocal, engine  # noqa: E402
from app.services.demo_service import DEMO_MANAGER_PASSWORD, seed_demo  # noqa: E402


def main():
    config = get_config()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--file", default=config.DEMO_DATASET_PATH, help="CSV/Excel file to load (default: the sample)")
    parser.add_argument("--reload", action="store_true", help="load the file even if the store already has data")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        r = seed_demo(db, os.path.abspath(args.file), reload=args.reload)
    finally:
        db.close()

    print("Pairly demo is ready")
    print(f"  Super admin   : {r['admin_email']} (password from SUPER_ADMIN_PASSWORD)")
    print(f"  Demo manager  : {r['manager_email']} / {DEMO_MANAGER_PASSWORD}")
    print(f"  Dataset       : {'loaded now' if r['dataset_loaded'] else 'already loaded'} "
          f"({r['rows']:,} rows, {r['transactions']:,} baskets, {r['products']:,} products)")
    print(f"  Analytics     : {r['rules']} association rules, {r['segments']} customer segments")


if __name__ == "__main__":
    main()

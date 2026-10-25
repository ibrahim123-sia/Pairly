"""Create the Pairly demo store, its manager and its dataset.

Used by scripts/seed_demo.py and by the test suite. Safe to run many times.
"""
import logging
import os

from sqlalchemy.orm import Session

from app.models import Dataset, Store, User, UserRole
from app.services import analytics_service, auth_service, dataset_service, insights_service, mba_service

logger = logging.getLogger("pairly.demo")

DEMO_STORE_SLUG = "demo-store"
DEMO_STORE_NAME = "Demo Store"
DEMO_MANAGER_EMAIL = os.environ.get("DEMO_MANAGER_EMAIL", "demo@example.com")
DEMO_MANAGER_PASSWORD = os.environ.get("DEMO_MANAGER_PASSWORD", "Demo@12345")


class _LocalUpload:
    """Minimal stand-in for FastAPI's UploadFile."""

    def __init__(self, path):
        self.filename = os.path.basename(path)
        self.file = open(path, "rb")

    def close(self):
        self.file.close()


def _has_usable_dataset(db: Session, store: Store) -> bool:
    """True if the active dataset's file is on disk or can be restored from storage (R2)."""
    if not store.active_dataset_id:
        return False
    ds = db.get(Dataset, store.active_dataset_id)
    return bool(ds and dataset_service.ensure_local_file(db, ds))


def seed_demo(db: Session, dataset_path: str, reload: bool = False, check: bool = True) -> dict:
    admin = auth_service.ensure_super_admin(db)

    store = db.query(Store).filter(Store.slug == DEMO_STORE_SLUG).first()
    if not store:
        store = Store(
            name=DEMO_STORE_NAME,
            slug=DEMO_STORE_SLUG,
            description="Pairly demo store loaded with the Online Retail II sample dataset.",
            contact_email="demo@example.com",
            theme_mode="light",
            brand_primary_color="#2563eb",
            is_active=True,
            created_by_user_id=admin.id,
        )
        db.add(store)
        db.commit()

    manager = db.query(User).filter(User.email == DEMO_MANAGER_EMAIL).first()
    if not manager:
        manager = User(
            email=DEMO_MANAGER_EMAIL,
            password_hash=auth_service.hash_password(DEMO_MANAGER_PASSWORD),
            role=UserRole.STORE_MANAGER,
            full_name="Demo Manager",
            is_email_verified=True,
            is_active=True,
            must_change_password=False,
            store_id=store.id,
        )
        db.add(manager)
        db.commit()

    loaded = False
    if reload or not _has_usable_dataset(db, store):
        if not os.path.exists(dataset_path):
            raise FileNotFoundError(f"Demo dataset not found: {dataset_path}")
        logger.info("Loading demo dataset from %s", dataset_path)
        upload = _LocalUpload(dataset_path)
        try:
            result = dataset_service.process_upload(db, store, upload, manager)
        finally:
            upload.close()
        if not result.get("ok"):
            raise RuntimeError(f"Could not load demo dataset: {result.get('error')}")
        # process_upload only activates the first dataset; a reload must win too.
        dataset_service.activate_dataset(db, store, result["dataset"], actor=manager)
        loaded = True

    report = {"admin_email": admin.email, "store_id": store.id, "manager_email": manager.email, "dataset_loaded": loaded}
    if check:
        report.update(_analytics_check(db, store))
    return report


def _analytics_check(db: Session, store: Store) -> dict:
    """Run the main analytics once so we know the demo works end to end."""
    df, dataset = dataset_service.get_active_dataframe(db, store)
    if df is None:
        raise RuntimeError("Demo store has no usable active dataset")
    summary = analytics_service.compute_summary(df)
    rules = mba_service.compute_association_rules(df, 0.01, 0.3, 1.0, 50)
    rfm = insights_service.compute_rfm(df)
    return {
        "rows": int(len(df)),
        "transactions": summary.get("total_transactions", 0),
        "products": summary.get("total_products", 0),
        "rules": rules.get("metadata", {}).get("total_rules_found", len(rules.get("data", []))),
        "segments": len(rfm.get("segments", [])),
    }

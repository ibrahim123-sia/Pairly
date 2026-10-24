import os
import sys

# Ensure backend directory is in the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal, Base, engine
from app.models import User, Store, UserRole
from app.services import auth_service, dataset_service
from config import get_config

config = get_config()


def seed():
    # Make sure all tables are created
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        admin = auth_service.ensure_super_admin(db)
        print(f"Super admin ready: {admin.email}")

        store = db.query(Store).filter(Store.slug == "demo-store").first()
        if not store:
            store = Store(
                name="Demo Store",
                slug="demo-store",
                description="Pairly demo store loaded with the Online Retail II sample dataset.",
                contact_email="demo@example.com",
                theme_mode="light",
                brand_primary_color="#2563eb",
                is_active=True,
                created_by_user_id=admin.id,
            )
            db.add(store)
            db.flush()

        manager = db.query(User).filter(User.email == "demo@example.com").first()
        if not manager:
            manager = User(
                email="demo@example.com",
                password_hash=auth_service.hash_password("Demo@12345"),
                role=UserRole.STORE_MANAGER,
                full_name="Demo Manager",
                is_email_verified=True,
                is_active=True,
                must_change_password=False,
                store_id=store.id,
            )
            db.add(manager)
            db.commit()

        print("Demo store ready (slug=demo-store, manager=demo@example.com / Demo@12345)")

        legacy_csv = None
        candidates = [
            os.path.join(config.BASE_DIR, "..", "data", "Online_Retail_II_Cleaned.csv"),
            os.path.join(config.DATA_DIR, "Online_Retail_II_Cleaned.csv"),
            os.path.join(config.BASE_DIR, "data", "Online_Retail_II_Cleaned.csv"),
        ]
        for p in candidates:
            if os.path.exists(p):
                legacy_csv = p
                break

        if legacy_csv and not store.active_dataset_id:
            print(f"Seeding dataset from {legacy_csv}...")

            class MockUploadFile:
                def __init__(self, filepath):
                    self.filename = os.path.basename(filepath)
                    self.file = open(filepath, "rb")

            upload_file = MockUploadFile(legacy_csv)
            try:
                result = dataset_service.process_upload(db, store, upload_file, manager)
                if result.get("ok"):
                    print(f"Seeded dataset: {result['dataset'].original_filename} ({result['dataset'].row_count} rows)")
                else:
                    print(f"Could not seed dataset: {result.get('error')}")
            finally:
                upload_file.file.close()
        elif not legacy_csv:
            print("Legacy CSV not found; skipping dataset seed.")
        else:
            print("Demo store already has an active dataset; skipping CSV seed.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()

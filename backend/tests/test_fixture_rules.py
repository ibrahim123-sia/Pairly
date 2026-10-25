"""Known rules and bundles from tests/fixtures/transactions_small.csv.

The fixture plants two product pairs whose numbers can be worked out by hand
(see fixtures/make_fixture.py). The file goes through the real upload
pipeline into its own store, so these tests cover cleaning, mapping, Apriori
and the API together.
"""
import os

import pytest

from app.models import Store, User, UserRole
from app.services import auth_service, dataset_service, insights_service, mba_service
from app.services.demo_service import _LocalUpload
from conftest import auth

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "transactions_small.csv")
GREEN = "GREEN REGENCY TEACUP AND SAUCER"
ROSES = "ROSES REGENCY TEACUP AND SAUCER"
RED_BAG = "JUMBO BAG RED RETROSPOT"
PINK_BAG = "JUMBO BAG PINK POLKADOT"
MANAGER = ("fixture-manager@example.com", "Fixture@12345")

# Thresholds that keep only the planted pairs (filler rules have lift ~1.07).
STRICT = {"min_support": 0.05, "min_confidence": 0.5, "min_lift": 1.5}


@pytest.fixture(scope="module")
def fixture_store(seeded):
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        store = db.query(Store).filter_by(slug="fixture-store").first()
        if store is None:
            store = Store(name="Fixture Store", slug="fixture-store", is_active=True)
            db.add(store)
            db.commit()
            manager = User(email=MANAGER[0], password_hash=auth_service.hash_password(MANAGER[1]),
                           role=UserRole.STORE_MANAGER, full_name="Fixture Manager", store_id=store.id)
            db.add(manager)
            db.commit()
            upload = _LocalUpload(FIXTURE)
            try:
                result = dataset_service.process_upload(db, store, upload, manager)
            finally:
                upload.close()
            assert result["ok"], result
        return store.id
    finally:
        db.close()


@pytest.fixture(scope="module")
def df(fixture_store):
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        frame, _ = dataset_service.get_active_dataframe(db, db.get(Store, fixture_store))
        return frame
    finally:
        db.close()


def test_fixture_loads_cleanly(df):
    assert len(df) == 315
    assert df["InvoiceNo"].nunique() == 150


def test_known_association_rules(df):
    res = mba_service.compute_association_rules(df, limit=50, **STRICT)
    rules = {(r["antecedent"], r["consequent"]): r for r in res["data"]}
    assert set(rules) == {(GREEN, ROSES), (PINK_BAG, RED_BAG)}

    teacups = rules[(GREEN, ROSES)]
    assert teacups["support"] == 0.24            # 36 of 150 baskets
    assert teacups["confidence"] == 0.9          # 36 of the 40 green-teacup baskets
    assert teacups["lift"] == 3.0                # 0.9 / (45 / 150)
    assert teacups["antecedent_support"] == round(40 / 150, 4)
    assert teacups["consequent_support"] == 0.3

    bags = rules[(PINK_BAG, RED_BAG)]
    assert bags["support"] == 0.16               # 24 of 150
    assert bags["confidence"] == 0.8             # 24 of 30
    assert bags["lift"] == 2.4                   # 0.8 / (50 / 150)

    # Strongest rule first
    assert (res["data"][0]["antecedent"], res["data"][0]["consequent"]) == (GREEN, ROSES)


def test_reverse_direction_is_deduplicated(df):
    """ROSES -> GREEN (confidence 36/45 = 0.8) is the same pair; only the stronger direction is kept."""
    res = mba_service.compute_association_rules(df, limit=50, **STRICT)
    assert (ROSES, GREEN) not in {(r["antecedent"], r["consequent"]) for r in res["data"]}


def test_known_bundles(df):
    bundles = mba_service.compute_product_bundles(df, limit=50, **STRICT)["bundles"]
    assert [b["products"] for b in bundles] == [[GREEN, ROSES], [PINK_BAG, RED_BAG]]
    assert [b["transaction_count"] for b in bundles] == [36, 24]
    assert [b["bundle_id"] for b in bundles] == ["B001", "B002"]


def test_recommendations_for_green_teacup(df):
    res = insights_service.compute_recommendations(df, GREEN, limit=3)
    top = res["recommendations"][0]
    assert res["target"] == GREEN and res["metadata"]["target_transactions"] == 40
    assert top["product"] == ROSES
    assert top["co_purchase_count"] == 36
    assert top["confidence"] == 0.9
    assert top["lift"] == 3.0


def test_bundle_simulator_counts(df):
    res = insights_service.simulate_bundle(df, [GREEN, ROSES], 10)
    assert res["current"]["co_purchase_baskets"] == 36
    assert res["current"]["any_member_baskets"] == 49      # invoices 0..48
    assert res["current"]["co_purchase_rate"] == 24.0


def test_rules_through_the_api(client, fixture_store):
    r = client.post("/api/auth/login", json={"email": MANAGER[0], "password": MANAGER[1]})
    token = r.json()["access_token"]
    body = client.get("/api/analytics/association_rules", headers=auth(token), params={**STRICT, "limit": 10}).json()
    assert [(x["antecedent"], x["consequent"], x["confidence"], x["lift"]) for x in body["data"]] == [
        (GREEN, ROSES, 0.9, 3.0),
        (PINK_BAG, RED_BAG, 0.8, 2.4),
    ]
    bundles = client.get("/api/analytics/product_bundles_filtered", headers=auth(token),
                         params={**STRICT, "limit": 10}).json()["bundles"]
    assert [b["transaction_count"] for b in bundles] == [36, 24]

"""Ask Pairly tools: store scoping, argument filtering and privacy."""
import csv
import json
import os

import pytest

from app.models import Store, User, UserRole
from app.services import auth_service, dataset_service
from app.services.ai.tools import TOOLS, ToolContext, parse_arguments, run_tool, tool_specs
from app.services.demo_service import DEMO_STORE_SLUG, _LocalUpload

OTHER_PRODUCT_PREFIX = "OTHERSTORE ONLY"


@pytest.fixture(scope="module")
def other_store(seeded, tmp_path_factory):
    """A second store whose products never appear in the demo data."""
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        store = db.query(Store).filter_by(slug="other-store").first()
        if store is None:
            store = Store(name="Other Store", slug="other-store", is_active=True)
            db.add(store)
            db.commit()
            manager = User(email="other-manager@example.com", password_hash=auth_service.hash_password("Other@12345"),
                           role=UserRole.STORE_MANAGER, full_name="Other Manager", store_id=store.id)
            db.add(manager)
            db.commit()

            path = os.path.join(tmp_path_factory.mktemp("other"), "other.csv")
            with open(path, "w", newline="") as f:
                w = csv.writer(f)
                w.writerow(["Invoice", "Description", "Quantity", "InvoiceDate", "Price", "CustomerID", "Country"])
                for inv in range(300):
                    for item in range(3):
                        product = f"{OTHER_PRODUCT_PREFIX} ITEM {(inv + item) % 6}"
                        w.writerow([f"9{inv:05d}", product, 2, f"2011-{inv % 12 + 1:02d}-10 10:00", 3.5,
                                    f"C{inv % 40}", "Iceland"])
            upload = _LocalUpload(path)
            try:
                result = dataset_service.process_upload(db, store, upload, manager)
            finally:
                upload.close()
            assert result["ok"], result
        return store.id
    finally:
        db.close()


def _ctx(db, store_id):
    return ToolContext(db=db, store=db.get(Store, store_id))


def _demo_id(db):
    return db.query(Store).filter_by(slug=DEMO_STORE_SLUG).first().id


def _text(result):
    return json.dumps(result)


ALL_TOOL_CALLS = [
    ("get_association_rules", {}),
    ("get_bundles", {}),
    ("get_recommendations_for_product", {"product": "ITEM"}),
    ("get_revenue_breakdown", {}),
    ("get_seasonal_trend", {}),
    ("get_rfm_segments", {}),
    ("get_top_products", {}),
]


def test_every_tool_is_registered_and_has_no_store_argument():
    names = {spec["function"]["name"] for spec in tool_specs()}
    assert names == set(TOOLS) == {name for name, _ in ALL_TOOL_CALLS}
    for spec in tool_specs():
        props = spec["function"]["parameters"]["properties"]
        assert not any("store" in p for p in props), spec["function"]["name"]


@pytest.mark.parametrize("name, args", ALL_TOOL_CALLS)
def test_store_a_never_reads_store_b(db, other_store, name, args):
    demo_id = _demo_id(db)
    # The model "asks" for the other store's data. The id must be ignored.
    hostile = json.dumps({**args, "store_id": other_store, "store": other_store})

    demo_result = _text(run_tool(_ctx(db, demo_id), name, hostile))
    assert OTHER_PRODUCT_PREFIX not in demo_result
    assert "Iceland" not in demo_result

    other_result = run_tool(_ctx(db, other_store), name, json.dumps({**args, "store_id": demo_id}))
    assert "error" not in other_result, other_result
    other_text = _text(other_result)
    assert "WHITE HANGING HEART" not in other_text
    assert "United Kingdom" not in other_text


def test_other_store_sees_its_own_products(db, other_store):
    result = run_tool(_ctx(db, other_store), "get_top_products", "{}")
    assert result["products"] and all(p["product"].startswith(OTHER_PRODUCT_PREFIX) for p in result["products"])


def test_unknown_arguments_are_dropped():
    assert parse_arguments("get_top_products", '{"limit": 3, "store_id": 99, "sql": "drop"}') == {"limit": 3}
    assert parse_arguments("get_rfm_segments", '{"store_id": 2}') == {}
    assert parse_arguments("get_bundles", "not json") == {}


def test_unknown_tool_returns_error(db):
    assert "error" in run_tool(_ctx(db, _demo_id(db)), "delete_everything", "{}")


def test_store_without_data_gets_a_clear_error(db):
    empty = db.query(Store).filter_by(slug="empty-store").first()
    if empty is None:
        empty = Store(name="Empty Store", slug="empty-store", is_active=True)
        db.add(empty)
        db.commit()
    result = run_tool(_ctx(db, empty.id), "get_bundles", "{}")
    assert "no active dataset" in result["error"].lower()


@pytest.mark.parametrize("name, args", ALL_TOOL_CALLS)
def test_tools_never_return_customer_ids(db, name, args):
    result = run_tool(_ctx(db, _demo_id(db)), name, json.dumps(args))
    keys = set()

    def walk(x):
        if isinstance(x, dict):
            keys.update(k.lower() for k in x)
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)

    walk(result)
    assert not keys & {"customerid", "customer_id", "top_customers", "email"}


def test_recommendations_and_rules_answer_a_bundle_question(db):
    ctx = _ctx(db, _demo_id(db))
    recs = run_tool(ctx, "get_recommendations_for_product", '{"product": "teacup"}')
    assert recs["matched"] is True and recs["recommendations"]
    rules = run_tool(ctx, "get_association_rules", '{"product": "teacup", "limit": 3}')
    assert all("TEACUP" in r["if_bought"] or "TEACUP" in r["then_also_bought"] for r in rules["rules"])

"""Shared pytest fixtures.

The environment is set before any app module is imported, so the whole run
uses a throwaway SQLite file and data folder, never sends email, and has no
LLM keys (tests that need an LLM inject a mock).
"""
import os
import shutil
import sys
import tempfile

_TMP = tempfile.mkdtemp(prefix="pairly-tests-")
os.environ.update({
    "APP_ENV": "development",
    "APP_DEBUG": "false",
    "DATABASE_URL": "sqlite:///" + os.path.join(_TMP, "test.sqlite").replace("\\", "/"),
    "DATA_DIR": os.path.join(_TMP, "data"),
    "MAIL_SUPPRESS_SEND": "true",
    "SUPER_ADMIN_EMAIL": "admin@example.com",
    "SUPER_ADMIN_PASSWORD": "Admin@12345",
    "SECRET_KEY": "test-secret",
    "JWT_SECRET_KEY": "test-jwt-secret",
    # Never let a developer's real keys leak into the test run.
    "LLM_PROVIDER": "none",
    "GROQ_API_KEY": "",
    "GEMINI_API_KEY": "",
    "LLM_BASE_URL": "",
})
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from config import get_config  # noqa: E402
from app.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.services.demo_service import DEMO_MANAGER_EMAIL, DEMO_MANAGER_PASSWORD, seed_demo  # noqa: E402

ADMIN = ("admin@example.com", "Admin@12345")
DEMO = (DEMO_MANAGER_EMAIL, DEMO_MANAGER_PASSWORD)


def pytest_sessionfinish(session, exitstatus):
    engine.dispose()
    shutil.rmtree(_TMP, ignore_errors=True)


@pytest.fixture(scope="session")
def seeded():
    """Demo store + manager with the sample dataset (set PAIRLY_TEST_DATASET to use another file)."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        path = os.environ.get("PAIRLY_TEST_DATASET") or get_config().DEMO_DATASET_PATH
        return seed_demo(db, path, check=False)
    finally:
        db.close()


@pytest.fixture(scope="session")
def client(seeded):
    with TestClient(app) as c:
        yield c


def _login(client, email, password):
    r = client.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()


@pytest.fixture(scope="session")
def admin_token(client):
    return _login(client, *ADMIN)["access_token"]


@pytest.fixture(scope="session")
def demo_login(client):
    return _login(client, *DEMO)


@pytest.fixture(scope="session")
def demo_token(demo_login):
    return demo_login["access_token"]


def auth(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def db():
    s = SessionLocal()
    try:
        yield s
    finally:
        s.close()

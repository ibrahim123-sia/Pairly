"""Cloudflare runtime pieces: R2 dataset storage and the cron endpoint."""
import os
import shutil
import uuid
from datetime import datetime, timezone

import pytest

from app import config as cfg
from app.models import Dataset, ScheduledJob, Store, User, UserRole
from app.routers import internal
from app.services import auth_service, cache_service, dataset_service, scheduler_service
from app.services.demo_service import _LocalUpload
from app.services.storage import LocalStorage, R2Storage, dataset_key, set_storage

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "transactions_small.csv")


class FolderStorage:
    """Stands in for R2: keeps 'uploaded' files in a temp folder."""

    name = "fake-r2"

    def __init__(self, root):
        self.root = root
        self.downloads = 0

    def _path(self, key):
        return os.path.join(self.root, key.replace("/", os.sep))

    def upload(self, local_path, key):
        os.makedirs(os.path.dirname(self._path(key)), exist_ok=True)
        shutil.copyfile(local_path, self._path(key))

    def download(self, key, local_path):
        if not os.path.exists(self._path(key)):
            return False
        self.downloads += 1
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        shutil.copyfile(self._path(key), local_path)
        return True

    def delete(self, key):
        if os.path.exists(self._path(key)):
            os.remove(self._path(key))


@pytest.fixture
def r2(tmp_path):
    fake = FolderStorage(str(tmp_path / "bucket"))
    set_storage(fake)
    yield fake
    set_storage(LocalStorage())


@pytest.fixture
def store_with_manager(db, seeded):
    store = Store(name="Cloud Store", slug=f"cloud-{uuid.uuid4().hex[:10]}", is_active=True)
    db.add(store)
    db.commit()
    user = User(email=f"{store.slug}@example.com", password_hash=auth_service.hash_password("Cloud@12345"),
                role=UserRole.STORE_MANAGER, full_name="Cloud", store_id=store.id)
    db.add(user)
    db.commit()
    return store, user


def _upload(db, store, user):
    up = _LocalUpload(FIXTURE)
    try:
        res = dataset_service.process_upload(db, store, up, user)
    finally:
        up.close()
    assert res["ok"], res
    return res["dataset"]


def _wipe_local(store, ds):
    os.remove(ds.parquet_path)
    cache_service.invalidate_store(store.id)


def test_upload_is_copied_to_r2_and_restored_after_disk_wipe(db, r2, store_with_manager):
    store, user = store_with_manager
    ds = _upload(db, store, user)
    assert os.path.exists(r2._path(dataset_key(store.id, ds.id)))

    _wipe_local(store, ds)  # what a sleeping Cloudflare container does to its disk
    df, active = dataset_service.get_active_dataframe(db, store)
    assert df is not None and len(df) == 315 and active.id == ds.id
    assert r2.downloads == 1 and os.path.exists(ds.parquet_path)


def test_missing_everywhere_means_no_data(db, r2, store_with_manager):
    store, user = store_with_manager
    ds = _upload(db, store, user)
    r2.delete(dataset_key(store.id, ds.id))
    _wipe_local(store, ds)
    assert dataset_service.get_active_dataframe(db, store)[0] is None


def test_deleting_a_dataset_removes_it_from_r2(db, r2, store_with_manager):
    store, user = store_with_manager
    first = _upload(db, store, user)
    second = _upload(db, store, user)          # first stays active
    ok, err = dataset_service.delete_dataset(db, store, second, actor=user)
    assert ok, err
    assert not os.path.exists(r2._path(dataset_key(store.id, second.id)))
    assert os.path.exists(r2._path(dataset_key(store.id, first.id)))


def test_demo_seed_restores_instead_of_reloading(db, r2):
    from app.services.demo_service import DEMO_STORE_SLUG, seed_demo

    store = db.query(Store).filter_by(slug=DEMO_STORE_SLUG).one()
    ds = db.get(Dataset, store.active_dataset_id)
    r2.upload(ds.parquet_path, dataset_key(store.id, ds.id))
    _wipe_local(store, ds)
    count_before = db.query(Dataset).filter_by(store_id=store.id).count()

    report = seed_demo(db, cfg.get_config().DEMO_DATASET_PATH, check=False)
    assert report["dataset_loaded"] is False
    assert db.query(Dataset).filter_by(store_id=store.id).count() == count_before


class StubS3:
    def __init__(self, missing=False):
        self.calls, self.missing = [], missing

    def upload_file(self, path, bucket, key):
        self.calls.append(("upload", bucket, key))

    def download_file(self, bucket, key, path):
        from botocore.exceptions import ClientError
        if self.missing:
            raise ClientError({"Error": {"Code": "404"}}, "GetObject")
        self.calls.append(("download", bucket, key))
        open(path, "wb").write(b"PAR1")

    def delete_object(self, Bucket, Key):
        self.calls.append(("delete", Bucket, Key))


def test_r2_storage_uses_bucket_and_key(tmp_path):
    s3 = StubS3()
    store = R2Storage("acct", "id", "secret", "pairly-data", client=s3)
    store.upload(__file__, "stores/1/datasets/a.parquet")
    assert store.download("stores/1/datasets/a.parquet", str(tmp_path / "x" / "a.parquet")) is True
    store.delete("stores/1/datasets/a.parquet")
    assert [c[0] for c in s3.calls] == ["upload", "download", "delete"]
    assert all(c[1] == "pairly-data" for c in s3.calls)
    assert R2Storage("a", "b", "c", "d", client=StubS3(missing=True)).download("k", str(tmp_path / "y")) is False


# ---------------- cron endpoint ----------------

def _job(db, store_id, cron, created, last_run=None, enabled=True):
    job = db.query(ScheduledJob).filter_by(store_id=store_id).first() or ScheduledJob(store_id=store_id)
    job.is_enabled, job.cron_expression, job.created_at, job.last_run_at = enabled, cron, created, last_run
    db.add(job)
    db.commit()
    return job


def test_due_jobs_follow_cron_and_last_run(db, store_with_manager):
    store, _ = store_with_manager
    now = datetime(2026, 10, 25, 9, 0, tzinfo=timezone.utc)
    _job(db, store.id, "0 2 * * *", created=datetime(2026, 10, 24, 12, 0))
    assert store.id in scheduler_service.due_store_ids(db, now)            # 02:00 today has passed
    _job(db, store.id, "0 2 * * *", created=datetime(2026, 10, 24, 12, 0), last_run=datetime(2026, 10, 25, 2, 0, 5))
    assert store.id not in scheduler_service.due_store_ids(db, now)        # already ran today
    _job(db, store.id, "0 2 * * *", created=datetime(2026, 10, 25, 8, 0))
    assert store.id not in scheduler_service.due_store_ids(db, now)        # new job waits for tomorrow
    _job(db, store.id, "0 2 * * *", created=datetime(2026, 10, 1), enabled=False)
    assert store.id not in scheduler_service.due_store_ids(db, now)


def test_cron_endpoint_auth_and_run(client, db, store_with_manager, monkeypatch):
    store, _ = store_with_manager
    url = "/api/internal/scheduled-jobs/run"
    monkeypatch.setattr(cfg.Config, "CRON_SECRET", None)
    assert client.post(url).status_code == 404                              # switched off without a secret

    monkeypatch.setattr(cfg.Config, "CRON_SECRET", "s3cret-value")
    assert client.post(url, headers={"X-Cron-Secret": "wrong"}).status_code == 401
    assert client.post(url).status_code == 401

    ran = []
    monkeypatch.setattr(scheduler_service, "run_reanalysis", ran.append)

    class Now:
        def __init__(self, target, args, daemon):
            self.target, self.args = target, args

        def start(self):
            self.target(*self.args)

    monkeypatch.setattr(internal.threading, "Thread", Now)
    _job(db, store.id, "0 2 * * *", created=datetime(2026, 1, 1))
    r = client.post(url, headers={"X-Cron-Secret": "s3cret-value"})
    assert r.status_code == 202 and store.id in r.json()["due_store_ids"] and store.id in ran
    _job(db, store.id, "0 2 * * *", created=datetime(2026, 1, 1), enabled=False)


def test_external_mode_does_not_start_apscheduler(monkeypatch):
    monkeypatch.setattr(cfg.Config, "SCHEDULER_MODE", "external")
    monkeypatch.setattr(scheduler_service, "_scheduler", None)
    assert scheduler_service.init_scheduler() is None

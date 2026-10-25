"""Where uploaded datasets live long-term.

Datasets are always read from a local Parquet file. With STORAGE_BACKEND=r2
each file is also kept in a Cloudflare R2 bucket (S3-compatible API), and
downloaded again when the local copy is missing. That matters on Cloudflare
Containers, whose disk is wiped whenever the container sleeps.

    STORAGE_BACKEND       local | r2   (default: r2 when R2_BUCKET is set)
    R2_ACCOUNT_ID         Cloudflare account id
    R2_ACCESS_KEY_ID      R2 API token: access key id
    R2_SECRET_ACCESS_KEY  R2 API token: secret access key
    R2_BUCKET             bucket name
"""
import logging
import os

from config import get_config

logger = logging.getLogger("pairly.storage")


def dataset_key(store_id, dataset_id):
    return f"stores/{store_id}/datasets/{dataset_id}.parquet"


class StorageError(Exception):
    pass


class LocalStorage:
    """Files only on the local disk (development, docker compose)."""

    name = "local"

    def upload(self, local_path, key):
        pass

    def download(self, key, local_path):
        return os.path.exists(local_path)

    def delete(self, key):
        pass


class R2Storage:
    """Cloudflare R2 through its S3-compatible API."""

    name = "r2"

    def __init__(self, account_id, access_key_id, secret_access_key, bucket, client=None):
        if client is None:
            import boto3
            from botocore.config import Config as BotoConfig

            client = boto3.client(
                "s3",
                endpoint_url=f"https://{account_id}.r2.cloudflarestorage.com",
                aws_access_key_id=access_key_id,
                aws_secret_access_key=secret_access_key,
                region_name="auto",
                config=BotoConfig(signature_version="s3v4", retries={"max_attempts": 3, "mode": "standard"},
                                  connect_timeout=10, read_timeout=60),
            )
        self.client = client
        self.bucket = bucket

    def upload(self, local_path, key):
        try:
            self.client.upload_file(local_path, self.bucket, key)
        except Exception as exc:
            raise StorageError(f"Could not save the file to storage: {exc}") from exc

    def download(self, key, local_path):
        from botocore.exceptions import ClientError

        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        tmp = local_path + ".part"
        try:
            self.client.download_file(self.bucket, key, tmp)
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") in ("404", "NoSuchKey", "NotFound"):
                return False
            raise StorageError(f"Could not read the file from storage: {exc}") from exc
        os.replace(tmp, local_path)
        return True

    def delete(self, key):
        try:
            self.client.delete_object(Bucket=self.bucket, Key=key)
        except Exception as exc:
            logger.warning("Could not delete %s from R2: %s", key, exc)


_storage = None


def get_storage():
    global _storage
    if _storage is None:
        config = get_config()
        if config.STORAGE_BACKEND == "r2":
            missing = [k for k in ("R2_ACCOUNT_ID", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_BUCKET")
                       if not getattr(config, k)]
            if missing:
                raise RuntimeError("STORAGE_BACKEND=r2 needs " + ", ".join(missing))
            _storage = R2Storage(config.R2_ACCOUNT_ID, config.R2_ACCESS_KEY_ID, config.R2_SECRET_ACCESS_KEY,
                                 config.R2_BUCKET)
        else:
            _storage = LocalStorage()
        logger.info("Pairly storage: %s", _storage.name)
    return _storage


def set_storage(storage):
    """Swap the storage backend (tests)."""
    global _storage
    _storage = storage

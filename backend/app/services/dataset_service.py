"""Dataset upload pipeline: validate, clean, persist as parquet, activate."""
import os
import uuid

import pandas as pd
from sqlalchemy.orm import Session

from app.models import Dataset, DatasetStatus, Store
from app.services import cache_service
from app.services.audit_service import log_event
from app.utils.column_mapping import map_column_names, validate_required_columns
from app.utils.datetime_features import extract_datetime_features
from config import get_config

config = get_config()
ALLOWED_EXT = {".csv", ".xlsx", ".xls"}


def _store_dir(store_id):
    base = os.path.join(config.STORES_DIR, str(store_id), "datasets")
    os.makedirs(base, exist_ok=True)
    return base


def _load_file(file_storage, tmp_path, ext):
    # file_storage is expected to be a file-like object or FastAPI UploadFile.
    # We will write it to tmp_path first.
    if hasattr(file_storage, "file"):
        # UploadFile case
        with open(tmp_path, "wb") as f:
            f.write(file_storage.file.read())
    else:
        # Werkzeug/Flask fallback or binary
        file_storage.save(tmp_path)

    if ext == ".csv":
        for encoding in ("utf-8", "latin1", "ISO-8859-1", "cp1252"):
            try:
                return pd.read_csv(tmp_path, encoding=encoding, low_memory=False)
            except UnicodeDecodeError:
                continue
        raise ValueError("Could not decode CSV with any supported encoding")
    return pd.read_excel(tmp_path)


def process_upload(db: Session, store: Store, file_storage, uploader):
    # file_storage is FastAPI UploadFile
    filename = os.path.basename(file_storage.filename or "upload.csv")
    _, ext = os.path.splitext(filename.lower())
    if ext not in ALLOWED_EXT:
        return {"ok": False, "error": f"Unsupported file extension '{ext}'. Use CSV or Excel.", "code": "bad_extension"}

    dataset_id = str(uuid.uuid4())
    store_dir = _store_dir(store.id)
    tmp_path = os.path.join(store_dir, f"_tmp_{dataset_id}{ext}")

    dataset = Dataset(
        id=dataset_id,
        store_id=store.id,
        original_filename=filename,
        status=DatasetStatus.PROCESSING,
        uploaded_by_user_id=getattr(uploader, "id", None),
    )
    db.add(dataset)
    db.commit()

    try:
        df = _load_file(file_storage, tmp_path, ext)
        max_rows = config.MAX_ROWS_PER_DATASET
        if len(df) > max_rows:
            raise ValueError(f"Dataset has {len(df):,} rows; limit is {max_rows:,}.")

        df, column_mapping = map_column_names(df)
        missing = validate_required_columns(df)
        if missing:
            raise ValueError(f"Missing required columns: {', '.join(missing)}")

        if "Description" in df.columns:
            df["Description"] = df["Description"].astype(str).str.strip()
            df = df[~df["Description"].isin(["", "nan", "NaN", "null", "None"])]
            df = df[df["Description"].notna()]

        if "InvoiceNo" in df.columns:
            df["InvoiceNo"] = df["InvoiceNo"].astype(str)
            df = df[~df["InvoiceNo"].str.upper().str.startswith("C", na=False)]

        df["Quantity"] = pd.to_numeric(df["Quantity"], errors="coerce")
        df = df[df["Quantity"] > 0]
        df["Quantity"] = df["Quantity"].fillna(1).astype(int)

        df["UnitPrice"] = pd.to_numeric(df["UnitPrice"], errors="coerce")
        df = df[df["UnitPrice"] > 0]
        df["UnitPrice"] = df["UnitPrice"].fillna(0.0)

        if "CustomerID" in df.columns:
            df["CustomerID"] = df["CustomerID"].fillna("Unknown").astype(str)
        else:
            df["CustomerID"] = "Unknown"

        if "Country" in df.columns:
            df["Country"] = df["Country"].fillna("Unknown").astype(str)
        else:
            df["Country"] = "Unknown"

        df = extract_datetime_features(df)
        df["TotalAmount"] = df["Quantity"] * df["UnitPrice"]

        if len(df) == 0:
            raise ValueError("After cleaning, no rows remain in the dataset.")

        parquet_path = os.path.join(store_dir, f"{dataset_id}.parquet")
        df.to_parquet(parquet_path, compression="snappy", index=False)

        date_start = None
        date_end = None
        if "InvoiceDate" in df.columns:
            try:
                date_start = pd.to_datetime(df["InvoiceDate"]).min().to_pydatetime()
                date_end = pd.to_datetime(df["InvoiceDate"]).max().to_pydatetime()
            except Exception:
                pass

        dataset.parquet_path = parquet_path
        dataset.row_count = int(len(df))
        dataset.column_mapping = column_mapping
        dataset.date_range_start = date_start
        dataset.date_range_end = date_end
        dataset.file_size_bytes = os.path.getsize(parquet_path)
        dataset.status = DatasetStatus.READY
        dataset.validation_errors = None
        db.commit()

        if not store.active_dataset_id:
            store.active_dataset_id = dataset.id
            db.commit()

        cache_service.invalidate_store(store.id)
        log_event(
            db,
            "dataset_uploaded",
            actor=uploader,
            target_type="dataset",
            target_id=dataset.id,
            metadata={"filename": filename, "rows": dataset.row_count, "size": dataset.file_size_bytes},
        )
        return {"ok": True, "dataset": dataset, "warnings": column_mapping}
    except Exception as exc:
        db.rollback()
        dataset = db.get(Dataset, dataset_id)
        if dataset:
            dataset.status = DatasetStatus.FAILED
            dataset.validation_errors = {"error": str(exc)}
            db.commit()
        return {"ok": False, "error": str(exc), "code": "processing_failed", "dataset_id": dataset_id}
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass


def activate_dataset(db: Session, store: Store, dataset: Dataset, actor=None):
    if dataset.store_id != store.id:
        return False, "Dataset does not belong to this store"
    if dataset.status != DatasetStatus.READY:
        return False, "Dataset is not ready"
    store.active_dataset_id = dataset.id
    db.commit()
    cache_service.invalidate_store(store.id)
    log_event(db, "dataset_activated", actor=actor, target_type="dataset", target_id=dataset.id)
    return True, None


def delete_dataset(db: Session, store: Store, dataset: Dataset, actor=None):
    if dataset.store_id != store.id:
        return False, "Dataset does not belong to this store"
    if store.active_dataset_id == dataset.id:
        return False, "Cannot delete the active dataset; activate another first."
    parquet_path = dataset.parquet_path
    db.delete(dataset)
    db.commit()
    if parquet_path and os.path.exists(parquet_path):
        try:
            os.remove(parquet_path)
        except OSError:
            pass
    cache_service.invalidate_store(store.id, dataset.id)
    log_event(db, "dataset_deleted", actor=actor, target_type="dataset", target_id=dataset.id)
    return True, None


def get_active_dataframe(db: Session, store: Store):
    if not store.active_dataset_id:
        return None, None
    dataset = db.get(Dataset, store.active_dataset_id)
    if not dataset or dataset.status != DatasetStatus.READY:
        return None, dataset
    df = cache_service.load_dataframe(store.id, dataset.id, dataset.parquet_path)
    return df, dataset

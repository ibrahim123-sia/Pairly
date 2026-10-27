import os

import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, Response, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.config import get_config
from app.database import get_db
from app.dependencies import get_current_store, get_current_user
from app.models import Dataset, ScheduledJob, Store, User
from app.schemas import PDFExportRequest, ProfileUpdateRequest, ScheduledJobUpsertRequest
from app.services import dataset_service, export_service, scheduler_service
from app.services.audit_service import log_event

config = get_config()
router = APIRouter()


@router.get("/profile")
def get_profile(current_store: Store = Depends(get_current_store)):
    return current_store.to_dict(include_counts=True)


@router.patch("/profile")
def update_profile(
    request: Request,
    payload: ProfileUpdateRequest,
    current_store: Store = Depends(get_current_store),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    data = payload.dict(exclude_unset=True)
    for field in ("name", "description", "contact_email", "brand_primary_color"):
        if field in data:
            setattr(current_store, field, data[field] or None)
    if data.get("theme_mode") in ("light", "dark"):
        current_store.theme_mode = data["theme_mode"]
    db.commit()

    log_event(db, "profile_updated", actor=current_user, target_type="store", target_id=current_store.id, metadata=data, request=request)
    return current_store.to_dict(include_counts=True)


@router.get("/datasets")
def list_datasets(
    current_store: Store = Depends(get_current_store),
    db: Session = Depends(get_db),
):
    items = db.query(Dataset).filter(Dataset.store_id == current_store.id).order_by(Dataset.uploaded_at.desc()).all()
    return {
        "items": [d.to_dict(is_active=(d.id == current_store.active_dataset_id)) for d in items],
        "active_dataset_id": current_store.active_dataset_id,
    }


@router.post("/datasets/upload", status_code=status.HTTP_201_CREATED)
def upload_dataset(
    file: UploadFile = File(...),
    current_store: Store = Depends(get_current_store),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = dataset_service.process_upload(db, current_store, file, current_user)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    ds = result["dataset"]
    return {
        "ok": True,
        "dataset": ds.to_dict(is_active=(ds.id == current_store.active_dataset_id)),
        "warnings": result.get("warnings") or {},
    }


@router.post("/datasets/{dataset_id}/activate")
def activate_dataset(
    dataset_id: str,
    current_store: Store = Depends(get_current_store),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ds = db.get(Dataset, dataset_id)
    if not ds or ds.store_id != current_store.id:
        raise HTTPException(status_code=404, detail="Dataset not found")

    ok, err = dataset_service.activate_dataset(db, current_store, ds, actor=current_user)
    if not ok:
        raise HTTPException(status_code=400, detail=err)
    return {"ok": True}


@router.delete("/datasets/{dataset_id}")
def delete_dataset(
    dataset_id: str,
    current_store: Store = Depends(get_current_store),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ds = db.get(Dataset, dataset_id)
    if not ds or ds.store_id != current_store.id:
        raise HTTPException(status_code=404, detail="Dataset not found")

    ok, err = dataset_service.delete_dataset(db, current_store, ds, actor=current_user)
    if not ok:
        raise HTTPException(status_code=400, detail=err)
    return {"ok": True}


@router.get("/scheduled-job")
def get_scheduled_job(
    current_store: Store = Depends(get_current_store),
    db: Session = Depends(get_db),
):
    job = db.query(ScheduledJob).filter(ScheduledJob.store_id == current_store.id).first()
    return job.to_dict() if job else None


@router.put("/scheduled-job")
def upsert_scheduled_job(
    request: Request,
    payload: ScheduledJobUpsertRequest,
    current_store: Store = Depends(get_current_store),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    job = db.query(ScheduledJob).filter(ScheduledJob.store_id == current_store.id).first()
    if not job:
        job = ScheduledJob(store_id=current_store.id)
        db.add(job)

    job.is_enabled = bool(payload.is_enabled)
    job.cron_expression = payload.cron_expression.strip() if payload.cron_expression else "0 2 * * *"
    job.email_summary_to = payload.email_summary_to.strip() if payload.email_summary_to else None
    db.commit()

    if job.is_enabled:
        scheduler_service.register_job(job)
    else:
        scheduler_service.unregister_job(job.store_id)

    log_event(db, "scheduled_job_updated", actor=current_user, target_type="store", target_id=current_store.id, metadata={"enabled": job.is_enabled, "cron": job.cron_expression}, request=request)
    return job.to_dict()


@router.post("/exports/pdf")
def export_pdf(
    request: Request,
    payload: PDFExportRequest,
    current_store: Store = Depends(get_current_store),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    sections = payload.sections or ["summary", "top_rules", "top_products"]
    df, dataset = dataset_service.get_active_dataframe(db, current_store)
    if df is None:
        raise HTTPException(status_code=409, detail="No active dataset")

    from app.services import analytics_service, mba_service
    payloads = {}
    if "summary" in sections:
        payloads["summary"] = analytics_service.compute_summary(df)
    if "top_rules" in sections:
        rules = mba_service.compute_association_rules(df, limit=10)
        payloads["rules"] = rules.get("data", []) if isinstance(rules, dict) else []
    if "top_products" in sections:
        payloads["products"] = analytics_service.compute_top_products(df, limit=20).get("products", [])

    export_id, path = export_service.generate_pdf_report(current_store, sections, payloads)
    log_event(db, "export_generated", actor=current_user, target_type="store", target_id=current_store.id, metadata={"type": "pdf", "export_id": export_id}, request=request)
    return {
        "export_id": export_id,
        "download_url": f"/api/store/exports/{export_id}/download"
    }


@router.get("/exports/{export_id}/download")
def download_export(
    export_id: str,
    current_store: Store = Depends(get_current_store),
):
    path = os.path.join(config.STORES_DIR, str(current_store.id), "exports", f"{export_id}.pdf")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Export not found")
    return FileResponse(
        path,
        media_type="application/pdf",
        filename=f"{current_store.slug}-report-{export_id[:8]}.pdf"
    )


@router.get("/exports/csv")
def export_csv(
    request: Request,
    type: str = Query("top_products"),
    current_store: Store = Depends(get_current_store),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.services import analytics_service
    df, dataset = dataset_service.get_active_dataframe(db, current_store)
    if df is None:
        raise HTTPException(status_code=409, detail="No active dataset")

    kind = type
    if kind == "top_products":
        out_df = pd.DataFrame(analytics_service.compute_top_products(df, limit=200).get("products", []))
    elif kind == "summary":
        out_df = pd.DataFrame([analytics_service.compute_summary(df)])
    elif kind == "raw":
        out_df = df.head(50000)
    elif kind == "recommendations":
        from app.services import insights_service
        result = insights_service.compute_recommendations(df, product_name=None, limit=10)
        rows = []
        for prod, recs in (result.get("per_product") or {}).items():
            for r in recs:
                rows.append({
                    "source_product": prod,
                    "recommended_product": r["product"],
                    "co_purchase_count": r["co_purchase_count"],
                    "confidence": r["confidence"],
                    "lift": r["lift"],
                    "co_purchase_rate_pct": r["co_purchase_rate"],
                    "score": r["score"],
                })
        out_df = pd.DataFrame(rows)
    elif kind == "customer_segments":
        from app.services import insights_service
        result = insights_service.compute_rfm(df)
        out_df = pd.DataFrame(result.get("top_customers", []))
    else:
        raise HTTPException(status_code=400, detail="Unknown export type")

    buf = export_service.dataframe_to_csv_stream(out_df)
    log_event(db, "export_generated", actor=current_user, target_type="store", target_id=current_store.id, metadata={"type": kind}, request=request)
    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={current_store.slug}-{kind}.csv"},
    )

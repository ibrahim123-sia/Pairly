import re
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import super_admin_required
from app.models import AuditLog, Dataset, Store, User, UserRole
from app.schemas import CreateStoreRequest, DisableStoreRequest, ProfileUpdateRequest
from app.services import auth_service
from app.services.audit_service import log_event
from app.services.email_service import send_new_account_email, send_store_disabled_email

router = APIRouter()


def _slugify(name):
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "store"


def _unique_slug(db: Session, base: str):
    slug = base
    i = 1
    while db.query(Store).filter(Store.slug == slug).first() is not None:
        i += 1
        slug = f"{base}-{i}"
    return slug


def paginate(query, page: int, per_page: int):
    total = query.count()
    pages = (total + per_page - 1) // per_page if per_page else 0
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    return {
        "items": items,
        "page": page,
        "per_page": per_page,
        "total": total,
        "pages": pages,
    }


@router.get("/stores")
def list_stores(
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    current_user: User = Depends(super_admin_required),
    db: Session = Depends(get_db),
):
    q = db.query(Store).order_by(Store.created_at.desc())
    res = paginate(q, page, per_page)
    return {
        "items": [s.to_dict(include_counts=True) for s in res["items"]],
        "page": res["page"],
        "per_page": res["per_page"],
        "total": res["total"],
        "pages": res["pages"],
    }


@router.post("/stores", status_code=status.HTTP_201_CREATED)
def create_store(
    request: Request,
    payload: CreateStoreRequest,
    current_user: User = Depends(super_admin_required),
    db: Session = Depends(get_db),
):
    name = payload.name.strip()
    manager_email = payload.manager_email.lower().strip()
    manager_name = (payload.manager_full_name or payload.manager_name or "").strip() or manager_email.split("@")[0]
    description = (payload.description or "").strip() or None
    contact_email = (payload.contact_email or manager_email).lower().strip() or None
    theme_mode = payload.theme_mode or "light"
    brand_color = payload.brand_primary_color or None
    requested_slug = (payload.slug or "").strip().lower()

    if not name:
        raise HTTPException(status_code=400, detail="Store name is required")
    if not manager_email or "@" not in manager_email:
        raise HTTPException(status_code=400, detail="Valid manager email required")
    if db.query(User).filter(User.email == manager_email).first() is not None:
        raise HTTPException(status_code=409, detail="A user with this email already exists")

    slug_base = _slugify(requested_slug or name)
    slug = _unique_slug(db, slug_base)

    store = Store(
        name=name,
        slug=slug,
        description=description,
        contact_email=contact_email,
        theme_mode=theme_mode if theme_mode in ("light", "dark") else "light",
        brand_primary_color=brand_color,
        is_active=True,
        created_by_user_id=current_user.id,
    )
    db.add(store)
    db.flush()

    temp_password = auth_service.generate_temp_password()
    manager = User(
        email=manager_email,
        password_hash=auth_service.hash_password(temp_password),
        role=UserRole.STORE_MANAGER,
        full_name=manager_name,
        is_email_verified=True,
        is_active=True,
        must_change_password=True,
        store_id=store.id,
    )
    db.add(manager)
    db.commit()

    log_event(db, "store_created", actor=current_user, target_type="store", target_id=store.id, metadata={"name": store.name, "slug": store.slug}, request=request)
    log_event(db, "manager_created", actor=current_user, target_type="user", target_id=manager.id, metadata={"email": manager.email, "store_id": store.id}, request=request)

    sent, err = send_new_account_email(manager, store, temp_password, db=db)
    response = {
        "store": store.to_dict(include_counts=True),
        "manager": manager.to_dict(),
        "email_sent": sent,
    }
    if not sent:
        response["temp_password"] = temp_password
        response["email_error"] = err
    return response


@router.get("/stores/{store_id}")
def get_store(
    store_id: int,
    current_user: User = Depends(super_admin_required),
    db: Session = Depends(get_db),
):
    store = db.get(Store, store_id)
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")
    manager = next((u for u in store.users if u.role == UserRole.STORE_MANAGER), None)
    return {
        "store": store.to_dict(include_counts=True),
        "manager": manager.to_dict() if manager else None,
    }


@router.patch("/stores/{store_id}")
def update_store(
    store_id: int,
    request: Request,
    payload: ProfileUpdateRequest,
    current_user: User = Depends(super_admin_required),
    db: Session = Depends(get_db),
):
    store = db.get(Store, store_id)
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")

    data = payload.dict(exclude_unset=True)
    for field in ("name", "description", "contact_email", "brand_primary_color"):
        if field in data:
            setattr(store, field, data[field] or None)
    if data.get("theme_mode") in ("light", "dark"):
        store.theme_mode = data["theme_mode"]

    db.commit()
    log_event(db, "store_updated", actor=current_user, target_type="store", target_id=store.id, metadata=data, request=request)
    return store.to_dict(include_counts=True)


@router.post("/stores/{store_id}/disable")
def disable_store(
    store_id: int,
    request: Request,
    payload: DisableStoreRequest,
    current_user: User = Depends(super_admin_required),
    db: Session = Depends(get_db),
):
    store = db.get(Store, store_id)
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")

    reason = (payload.reason or "").strip() or None
    store.is_active = False
    store.disabled_at = datetime.utcnow()
    store.disabled_reason = reason
    db.commit()

    log_event(db, "store_disabled", actor=current_user, target_type="store", target_id=store.id, metadata={"reason": reason}, request=request)
    manager = next((u for u in store.users if u.role == UserRole.STORE_MANAGER), None)
    if manager:
        send_store_disabled_email(manager, store, reason, db=db)
    return store.to_dict(include_counts=True)


@router.post("/stores/{store_id}/enable")
def enable_store(
    store_id: int,
    request: Request,
    current_user: User = Depends(super_admin_required),
    db: Session = Depends(get_db),
):
    store = db.get(Store, store_id)
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")

    store.is_active = True
    store.disabled_at = None
    store.disabled_reason = None
    db.commit()

    log_event(db, "store_enabled", actor=current_user, target_type="store", target_id=store.id, request=request)
    return store.to_dict(include_counts=True)


@router.post("/stores/{store_id}/reset-manager-password")
def reset_manager_password(
    store_id: int,
    request: Request,
    current_user: User = Depends(super_admin_required),
    db: Session = Depends(get_db),
):
    store = db.get(Store, store_id)
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")

    manager = next((u for u in store.users if u.role == UserRole.STORE_MANAGER), None)
    if not manager:
        raise HTTPException(status_code=404, detail="Store has no manager")

    temp = auth_service.generate_temp_password()
    manager.password_hash = auth_service.hash_password(temp)
    manager.must_change_password = True
    manager.failed_login_count = 0
    manager.locked_until = None
    db.commit()

    log_event(db, "manager_password_reset", actor=current_user, target_type="user", target_id=manager.id, request=request)
    sent, err = send_new_account_email(manager, store, temp, db=db)
    resp = {"ok": True, "email_sent": sent}
    if not sent:
        resp["temp_password"] = temp
        resp["email_error"] = err
    return resp


@router.get("/audit-log")
def audit_log_list(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    actor_id: Optional[int] = Query(None),
    action: Optional[str] = Query(None),
    target_type: Optional[str] = Query(None),
    current_user: User = Depends(super_admin_required),
    db: Session = Depends(get_db),
):
    q = db.query(AuditLog).order_by(AuditLog.created_at.desc())
    if actor_id is not None:
        q = q.filter(AuditLog.actor_user_id == actor_id)
    if action:
        q = q.filter(AuditLog.action == action)
    if target_type:
        q = q.filter(AuditLog.target_type == target_type)

    res = paginate(q, page, per_page)
    return {
        "items": [a.to_dict() for a in res["items"]],
        "page": res["page"],
        "per_page": res["per_page"],
        "total": res["total"],
        "pages": res["pages"],
    }


@router.get("/stats")
def admin_stats(
    current_user: User = Depends(super_admin_required),
    db: Session = Depends(get_db),
):
    total_stores = db.query(Store).count()
    active_stores = db.query(Store).filter(Store.is_active.is_(True)).count()
    total_users = db.query(User).count()
    total_managers = db.query(User).filter(User.role == UserRole.STORE_MANAGER).count()
    total_datasets = db.query(Dataset).count()
    return {
        "total_stores": total_stores,
        "active_stores": active_stores,
        "disabled_stores": total_stores - active_stores,
        "total_users": total_users,
        "total_managers": total_managers,
        "total_datasets": total_datasets,
    }

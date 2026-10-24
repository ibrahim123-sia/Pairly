from fastapi import Request
from sqlalchemy.orm import Session

from app.models import AuditLog


def log_event(db: Session, action: str, actor=None, target_type=None, target_id=None, metadata=None, request: Request = None):
    ip = None
    ua = None
    if request is not None:
        ip = request.headers.get("X-Forwarded-For")
        if not ip and request.client:
            ip = request.client.host
        ua = (request.headers.get("user-agent") or "")[:512]

    entry = AuditLog(
        actor_user_id=getattr(actor, "id", None),
        actor_email_snapshot=getattr(actor, "email", None),
        action=action,
        target_type=target_type,
        target_id=str(target_id) if target_id is not None else None,
        ip_address=ip,
        user_agent=ua,
        meta=metadata or None,
    )
    db.add(entry)
    try:
        db.commit()
    except Exception:
        db.rollback()

"""AI switches, the per-store daily limit, and usage logging.

AI runs for a store only if all of these are true:
  1. an LLM provider is configured (env vars),
  2. the super admin's platform switch is on,
  3. the super admin has not turned AI off for that store,
  4. the store manager has AI on in Settings,
  5. the store is under its daily request limit (UTC day).
"""
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import get_config
from app.models import AIUsageLog, PlatformSetting, Store, StoreAISettings

PLATFORM_AI_KEY = "ai_enabled"


@dataclass
class AIStatus:
    available: bool
    reason: Optional[str]  # None when available
    provider: Optional[str]
    model: Optional[str]
    platform_enabled: bool
    admin_store_enabled: bool
    store_enabled: bool
    used_today: int
    daily_limit: int

    def to_dict(self):
        return asdict(self)


REASON_TEXT = {
    "not_configured": "No AI provider is configured on the server.",
    "platform_disabled": "AI is turned off for the whole platform by the administrator.",
    "admin_disabled": "AI is turned off for this store by the administrator.",
    "store_disabled": "AI is turned off in this store's settings.",
    "limit_reached": "This store has used all of today's AI requests.",
}


def platform_enabled(db: Session) -> bool:
    row = db.get(PlatformSetting, PLATFORM_AI_KEY)
    if row is None or row.value is None:
        return get_config().AI_ENABLED
    return bool(row.value)


def set_platform_enabled(db: Session, enabled: bool):
    row = db.get(PlatformSetting, PLATFORM_AI_KEY)
    if row is None:
        row = PlatformSetting(key=PLATFORM_AI_KEY)
        db.add(row)
    row.value = bool(enabled)
    db.commit()


def store_settings(db: Session, store_id: int, create=False) -> Optional[StoreAISettings]:
    row = db.get(StoreAISettings, store_id)
    if row is None and create:
        row = StoreAISettings(store_id=store_id, ai_enabled=True, admin_ai_enabled=True)
        db.add(row)
        db.flush()
    return row


def daily_limit_for(row: Optional[StoreAISettings]) -> int:
    if row is not None and row.daily_limit is not None:
        return int(row.daily_limit)
    return get_config().AI_DAILY_REQUEST_LIMIT


def _today_start():
    now = datetime.utcnow()
    return datetime(now.year, now.month, now.day)


def used_today(db: Session, store_id: int) -> int:
    return db.query(func.count(AIUsageLog.id)).filter(
        AIUsageLog.store_id == store_id, AIUsageLog.created_at >= _today_start()
    ).scalar() or 0


def status_for(db: Session, store: Store, gateway) -> AIStatus:
    row = store_settings(db, store.id)
    admin_on = row.admin_ai_enabled if row else True
    store_on = row.ai_enabled if row else True
    plat_on = platform_enabled(db)
    limit = daily_limit_for(row)
    used = used_today(db, store.id)

    if gateway is None:
        reason = "not_configured"
    elif not plat_on:
        reason = "platform_disabled"
    elif not admin_on:
        reason = "admin_disabled"
    elif not store_on:
        reason = "store_disabled"
    elif used >= limit:
        reason = "limit_reached"
    else:
        reason = None
    return AIStatus(
        available=reason is None,
        reason=reason,
        provider=getattr(gateway, "provider", None),
        model=getattr(gateway, "model", None),
        platform_enabled=plat_on,
        admin_store_enabled=admin_on,
        store_enabled=store_on,
        used_today=used,
        daily_limit=limit,
    )


def log_usage(db: Session, store_id, user_id, feature, gateway, status, usage=None, llm_calls=0):
    db.add(AIUsageLog(
        store_id=store_id,
        user_id=user_id,
        feature=feature,
        provider=getattr(gateway, "provider", None),
        model=getattr(gateway, "model", None),
        status=status,
        llm_calls=llm_calls,
        prompt_tokens=getattr(usage, "prompt_tokens", 0) or 0,
        completion_tokens=getattr(usage, "completion_tokens", 0) or 0,
        total_tokens=getattr(usage, "total_tokens", 0) or 0,
    ))
    db.commit()


def usage_report(db: Session, days=30):
    """Per-store usage for the super-admin dashboard."""
    since = datetime.utcnow() - timedelta(days=days)
    today = _today_start()

    def agg(since_dt):
        rows = db.query(
            AIUsageLog.store_id,
            func.count(AIUsageLog.id),
            func.coalesce(func.sum(AIUsageLog.total_tokens), 0),
            func.coalesce(func.sum(AIUsageLog.prompt_tokens), 0),
            func.coalesce(func.sum(AIUsageLog.completion_tokens), 0),
        ).filter(AIUsageLog.created_at >= since_dt).group_by(AIUsageLog.store_id).all()
        return {r[0]: {"requests": int(r[1]), "tokens": int(r[2]), "prompt_tokens": int(r[3]),
                       "completion_tokens": int(r[4])} for r in rows}

    period, today_rows = agg(since), agg(today)
    fallbacks = dict(db.query(AIUsageLog.store_id, func.count(AIUsageLog.id)).filter(
        AIUsageLog.created_at >= since, AIUsageLog.status != "ok").group_by(AIUsageLog.store_id).all())
    by_feature = dict(db.query(AIUsageLog.feature, func.count(AIUsageLog.id)).filter(
        AIUsageLog.created_at >= since).group_by(AIUsageLog.feature).all())

    stores = []
    for s in db.query(Store).order_by(Store.name).all():
        row = store_settings(db, s.id)
        p = period.get(s.id, {})
        stores.append({
            "store_id": s.id,
            "store_name": s.name,
            "store_active": s.is_active,
            "store_ai_enabled": row.ai_enabled if row else True,
            "admin_ai_enabled": row.admin_ai_enabled if row else True,
            "daily_limit": daily_limit_for(row),
            "daily_limit_override": row.daily_limit if row else None,
            "requests_today": today_rows.get(s.id, {}).get("requests", 0),
            "requests": p.get("requests", 0),
            "tokens": p.get("tokens", 0),
            "prompt_tokens": p.get("prompt_tokens", 0),
            "completion_tokens": p.get("completion_tokens", 0),
            "fallbacks": int(fallbacks.get(s.id, 0)),
        })
    return {
        "days": days,
        "totals": {
            "requests": sum(x["requests"] for x in stores),
            "tokens": sum(x["tokens"] for x in stores),
            "requests_today": sum(x["requests_today"] for x in stores),
            "by_feature": {k: int(v) for k, v in by_feature.items()},
        },
        "stores": stores,
    }

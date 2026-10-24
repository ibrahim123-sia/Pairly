"""AI endpoints: insights card, Ask Pairly chat (SSE), AI settings and admin usage."""
import json
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import SessionLocal, get_db
from app.dependencies import get_current_store, get_current_user, super_admin_required
from app.models import Store, User
from app.services import dataset_service
from app.services.ai import usage
from app.services.ai.assistant import clean_history, run_chat
from app.services.ai.insights import get_insights
from app.services.ai.llm_gateway import Usage, get_gateway
from app.services.ai.tools import ToolContext
from app.services.audit_service import log_event

router = APIRouter()
admin_router = APIRouter()


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: List[ChatMessage] = Field(default_factory=list)


class StoreAIToggle(BaseModel):
    ai_enabled: bool


class AdminStoreAIUpdate(BaseModel):
    admin_ai_enabled: Optional[bool] = None
    daily_limit: Optional[int] = Field(default=None, ge=0, le=100000)
    reset_daily_limit: Optional[bool] = False


def _require_available(status):
    if status.available:
        return
    code = 429 if status.reason == "limit_reached" else 503 if status.reason == "not_configured" else 403
    raise HTTPException(status_code=code, detail={"code": status.reason, "message": usage.REASON_TEXT[status.reason]})


def _active_frame(db, store):
    df, dataset = dataset_service.get_active_dataframe(db, store)
    if df is None:
        raise HTTPException(status_code=409, detail="No active dataset for this store. Upload data first.")
    return df, dataset


def _thresholds(min_support, min_confidence, min_lift):
    # Same clamping as the analytics endpoints.
    return max(0.001, min_support), max(0.1, min_confidence), max(0.5, min_lift)


# ---------------- store manager ----------------

@router.get("/status")
def ai_status(store: Store = Depends(get_current_store), db: Session = Depends(get_db),
              gateway=Depends(get_gateway)):
    s = usage.status_for(db, store, gateway)
    return {**s.to_dict(), "message": usage.REASON_TEXT.get(s.reason)}


@router.get("/insights")
def insights(
    min_support: float = Query(0.01),
    min_confidence: float = Query(0.3),
    min_lift: float = Query(1.0),
    store: Store = Depends(get_current_store),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    gateway=Depends(get_gateway),
):
    df, dataset = _active_frame(db, store)
    return get_insights(db, store, user, df, dataset, gateway, *_thresholds(min_support, min_confidence, min_lift))


@router.post("/insights/regenerate")
def regenerate_insights(
    min_support: float = Query(0.01),
    min_confidence: float = Query(0.3),
    min_lift: float = Query(1.0),
    store: Store = Depends(get_current_store),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    gateway=Depends(get_gateway),
):
    df, dataset = _active_frame(db, store)
    return get_insights(db, store, user, df, dataset, gateway, *_thresholds(min_support, min_confidence, min_lift),
                        regenerate=True)


@router.post("/chat")
def chat(
    payload: ChatRequest,
    store: Store = Depends(get_current_store),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    gateway=Depends(get_gateway),
):
    _require_available(usage.status_for(db, store, gateway))
    history = clean_history([m.model_dump() for m in payload.messages])
    if not history or history[-1]["role"] != "user":
        raise HTTPException(status_code=400, detail="The last message must be a question from the user.")
    _active_frame(db, store)

    # The request's DB session may close before streaming finishes, so the
    # stream opens its own. The store id comes from the auth dependency only.
    store_id, user_id = store.id, user.id

    def stream():
        s = SessionLocal()
        try:
            ctx = ToolContext(db=s, store=s.get(Store, store_id))
            for event, data in run_chat(ctx, gateway, history):
                if event == "done":
                    u = data["usage"]
                    usage.log_usage(s, store_id, user_id, "chat", gateway, data["status"],
                                    Usage(u["prompt_tokens"], u["completion_tokens"], u["total_tokens"]),
                                    u["llm_calls"])
                yield f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False, default=str)}\n\n"
        finally:
            s.close()

    return StreamingResponse(stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@router.patch("/settings")
def update_store_ai(
    payload: StoreAIToggle,
    request: Request,
    store: Store = Depends(get_current_store),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    gateway=Depends(get_gateway),
):
    row = usage.store_settings(db, store.id, create=True)
    row.ai_enabled = payload.ai_enabled
    db.commit()
    log_event(db, "ai_settings_updated", actor=user, target_type="store", target_id=store.id,
              metadata={"ai_enabled": payload.ai_enabled}, request=request)
    s = usage.status_for(db, store, gateway)
    return {**s.to_dict(), "message": usage.REASON_TEXT.get(s.reason)}


# ---------------- super admin ----------------

def _admin_payload(db, gateway, days):
    return {
        "platform_enabled": usage.platform_enabled(db),
        "configured": gateway is not None,
        "provider": getattr(gateway, "provider", None),
        "model": getattr(gateway, "model", None),
        **usage.usage_report(db, days),
    }


@admin_router.get("")
def admin_ai_overview(days: int = Query(30, ge=1, le=365), admin: User = Depends(super_admin_required),
                      db: Session = Depends(get_db), gateway=Depends(get_gateway)):
    return _admin_payload(db, gateway, days)


@admin_router.patch("")
def admin_set_platform_ai(payload: StoreAIToggle, request: Request, admin: User = Depends(super_admin_required),
                          db: Session = Depends(get_db), gateway=Depends(get_gateway)):
    usage.set_platform_enabled(db, payload.ai_enabled)
    log_event(db, "platform_ai_updated", actor=admin, metadata={"ai_enabled": payload.ai_enabled}, request=request)
    return _admin_payload(db, gateway, 30)


@admin_router.patch("/stores/{store_id}")
def admin_update_store_ai(store_id: int, payload: AdminStoreAIUpdate, request: Request,
                          admin: User = Depends(super_admin_required), db: Session = Depends(get_db),
                          gateway=Depends(get_gateway)):
    if not db.get(Store, store_id):
        raise HTTPException(status_code=404, detail="Store not found")
    row = usage.store_settings(db, store_id, create=True)
    changes = payload.model_dump(exclude_unset=True)
    if payload.admin_ai_enabled is not None:
        row.admin_ai_enabled = payload.admin_ai_enabled
    if payload.reset_daily_limit:
        row.daily_limit = None
    elif "daily_limit" in changes:
        row.daily_limit = payload.daily_limit
    db.commit()
    log_event(db, "store_ai_updated", actor=admin, target_type="store", target_id=store_id, metadata=changes,
              request=request)
    return _admin_payload(db, gateway, 30)

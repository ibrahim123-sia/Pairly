"""Endpoints for platform timers, not for browsers.

POST /api/internal/scheduled-jobs/run is called by the Cloudflare Cron
Trigger when SCHEDULER_MODE=external. It needs the X-Cron-Secret header to
match CRON_SECRET, and is switched off (404) when CRON_SECRET is not set.
"""
import hmac
import threading

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.config import get_config
from app.database import get_db
from app.services import scheduler_service

router = APIRouter()


def _run_all(store_ids):
    for store_id in store_ids:
        scheduler_service.run_reanalysis(store_id)


@router.post("/scheduled-jobs/run", status_code=status.HTTP_202_ACCEPTED)
def run_scheduled_jobs(x_cron_secret: str = Header(default=""), db: Session = Depends(get_db)):
    secret = get_config().CRON_SECRET
    if not secret:
        raise HTTPException(status_code=404, detail="Not found")
    if not hmac.compare_digest(x_cron_secret.encode(), secret.encode()):
        raise HTTPException(status_code=401, detail="Invalid cron secret")
    due = scheduler_service.due_store_ids(db)
    if due:
        # Re-analysis can take a while; answer the timer right away.
        threading.Thread(target=_run_all, args=(due,), daemon=True).start()
    return {"due_store_ids": due}

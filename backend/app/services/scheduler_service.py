"""Scheduled re-analysis.

SCHEDULER_MODE=internal (default): APScheduler runs inside the API process.
SCHEDULER_MODE=external: nothing runs in-process; an outside timer (the
Cloudflare Cron Trigger) calls POST /api/internal/scheduled-jobs/run, which
runs the jobs that are due (see due_store_ids).
"""
import logging
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)
_scheduler = None


def get_scheduler():
    return _scheduler


def init_scheduler():
    global _scheduler
    if _scheduler is not None:
        return _scheduler
    from app.config import get_config
    if get_config().SCHEDULER_MODE == "external":
        logger.info("Scheduler: external mode, jobs run when /api/internal/scheduled-jobs/run is called")
        return None
    _scheduler = BackgroundScheduler(daemon=True, timezone="UTC")
    _scheduler.start()

    # Bootstrap enabled jobs
    from app.database import SessionLocal
    from app.models import ScheduledJob
    db = SessionLocal()
    try:
        jobs = db.query(ScheduledJob).filter(ScheduledJob.is_enabled.is_(True)).all()
        for job in jobs:
            register_job(job)
    except Exception as exc:
        logger.warning("Scheduler bootstrap deferred: %s", exc)
    finally:
        db.close()

    return _scheduler


def _job_id(store_id):
    return f"store_reanalysis_{store_id}"


def register_job(scheduled_job):
    if not _scheduler:
        return
    try:
        trigger = CronTrigger.from_crontab(scheduled_job.cron_expression)
    except Exception as exc:
        logger.warning("Invalid cron for store %s: %s", scheduled_job.store_id, exc)
        return
    _scheduler.add_job(
        run_reanalysis,
        trigger=trigger,
        args=[scheduled_job.store_id],
        id=_job_id(scheduled_job.store_id),
        replace_existing=True,
    )


def unregister_job(store_id):
    if not _scheduler:
        return
    try:
        _scheduler.remove_job(_job_id(store_id))
    except Exception:
        pass


def run_reanalysis(store_id):
    from app.database import SessionLocal
    from app.models import ScheduledJob, Store, User, UserRole
    from app.services import dataset_service
    from app.services.audit_service import log_event
    from app.services.email_service import send_scheduled_summary_email

    db = SessionLocal()
    try:
        store = db.get(Store, store_id)
        job = db.query(ScheduledJob).filter(ScheduledJob.store_id == store_id).first()
        if not store or not job:
            return
        job.last_run_status = "running"
        db.commit()
        try:
            df, dataset = dataset_service.get_active_dataframe(db, store)
            if df is None:
                raise RuntimeError("Store has no active dataset")

            from app.services import analytics_service, mba_service
            summary = analytics_service.compute_summary(df)
            rules = mba_service.compute_association_rules(df, limit=10)
            payload = {"summary": summary, "rules": rules.get("data", []) if isinstance(rules, dict) else [], "generated_at": datetime.utcnow().isoformat()}

            manager = db.query(User).filter(User.store_id == store.id, User.role == UserRole.STORE_MANAGER).first()
            recipient_email = job.email_summary_to or (manager.email if manager else None)
            if manager and recipient_email:
                original_email = manager.email
                manager.email = recipient_email
                send_scheduled_summary_email(manager, store, payload, db=db)
                manager.email = original_email

            job.last_run_status = "success"
            job.last_run_error = None
            log_event(db, "scheduled_job_run", target_type="store", target_id=store.id, metadata={"status": "success"})
        except Exception as exc:
            logger.exception("Scheduled re-analysis failed for store %s", store_id)
            job.last_run_status = "failed"
            job.last_run_error = str(exc)
            log_event(db, "scheduled_job_run", target_type="store", target_id=store.id, metadata={"status": "failed", "error": str(exc)})
        finally:
            job.last_run_at = datetime.utcnow()
            db.commit()
    finally:
        db.close()


def due_store_ids(db, now=None):
    """Stores whose enabled job has a cron fire time between its last run and now.

    A job that never ran counts from when it was created, so a new job waits
    for its first scheduled time instead of running at once.
    """
    from app.models import ScheduledJob

    now = now or datetime.now(timezone.utc)
    due = []
    for job in db.query(ScheduledJob).filter(ScheduledJob.is_enabled.is_(True)).all():
        try:
            trigger = CronTrigger.from_crontab(job.cron_expression, timezone="UTC")
        except ValueError:
            logger.warning("Invalid cron for store %s: %s", job.store_id, job.cron_expression)
            continue
        since = (job.last_run_at or job.created_at).replace(tzinfo=timezone.utc) + timedelta(seconds=1)
        next_fire = trigger.get_next_fire_time(None, since)
        if next_fire and next_fire <= now:
            due.append(job.store_id)
        upcoming = trigger.get_next_fire_time(None, now)
        job.next_run_at = upcoming.astimezone(timezone.utc).replace(tzinfo=None) if upcoming else None
    db.commit()
    return due

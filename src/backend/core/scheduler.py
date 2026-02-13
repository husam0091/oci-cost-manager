"""APScheduler setup and job registration."""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session

from core.database import SessionLocal
from core.models import Setting
from services.scanner import run_full_scan

_scheduler: BackgroundScheduler | None = None


def get_scheduler() -> BackgroundScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = BackgroundScheduler()
    return _scheduler


def ensure_default_settings(db: Session):
    from core.auth import hash_password
    from core.config import get_settings
    cfg = get_settings()
    s = db.query(Setting).filter(Setting.id == 1).one_or_none()
    if not s:
        s = Setting(
            id=1,
            username="admin",
            password_hash=hash_password("admin"),
            scan_interval_hours=8,
            oci_auth_mode="profile",
            oci_config_profile=cfg.oci_config_profile,
            oci_config_file=cfg.oci_config_file,
        )
        db.add(s); db.commit()


def schedule_scan():
    sched = get_scheduler()
    db = SessionLocal()
    try:
        ensure_default_settings(db)
        hours = db.query(Setting).filter(Setting.id == 1).one().scan_interval_hours or 8
    finally:
        db.close()
    if sched.get_job("scan_job"):
        sched.remove_job("scan_job")
    sched.add_job(lambda: _run_scan_job(), trigger=IntervalTrigger(hours=hours), id="scan_job", replace_existing=True)


def _run_scan_job():
    db = SessionLocal()
    try:
        run_full_scan(db)
    finally:
        db.close()


def start_scheduler():
    sched = get_scheduler()
    if not sched.running:
        sched.start()
    schedule_scan()

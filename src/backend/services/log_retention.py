"""Operator-configured retention for operational logs, never audit history."""

import os
from datetime import UTC, datetime, timedelta
from core.models import LogEvent


def prune_operational_logs(db, retention_days=None):
    days = (
        int(os.getenv("LOG_RETENTION_DAYS", "0"))
        if retention_days is None
        else retention_days
    )
    if days <= 0:
        return 0  # Retention requires an explicit policy; do not erase audit evidence by default.
    cutoff = datetime.now(UTC) - timedelta(days=days)
    removed = (
        db.query(LogEvent)
        .filter(LogEvent.ts < cutoff, LogEvent.log_type != "audit")
        .delete(synchronize_session=False)
    )
    db.commit()
    return removed


def retention_job():
    from core.database import SessionLocal

    with SessionLocal() as db:
        return prune_operational_logs(db)

"""Single-backend scan ownership, admission and restart recovery.

A kernel file lock survives threads and is released when the owning process dies.
This deployment runs one backend container; distributed replicas need a DB lease
or a durable queue before enabling more than one scanner container.
"""

import fcntl
import logging
import os
import threading
from datetime import UTC, datetime
from pathlib import Path

from core.database import SessionLocal
from core.models import ScanRun

logger = logging.getLogger(__name__)


def acquire_scan_lock():
    path = Path(os.getenv("SCAN_LOCK_PATH", "/tmp/oci-cost-manager-scan.lock"))
    handle = path.open("a")
    try:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        handle.close()
        return None
    return handle


def _fail_orphans(db):
    rows = db.query(ScanRun).filter(ScanRun.status == "running").all()
    for row in rows:
        row.status = "failed"
        row.finished_at = datetime.now(UTC)
        row.error_message = "Interrupted scan: no live scanner owns the execution lock. Previously committed compartments are retained."
    if rows:
        db.commit()
    return len(rows)


def recover_orphaned_scans(db):
    lease = acquire_scan_lock()
    if lease is None:
        return 0  # An active scan, however old, must never be failed by age alone.
    try:
        return _fail_orphans(db)
    finally:
        lease.close()


def start_inventory_scan():
    from services.scanner import run_full_scan

    lease = acquire_scan_lock()
    if lease is None:
        with SessionLocal() as db:
            row = (
                db.query(ScanRun)
                .filter(ScanRun.status == "running")
                .order_by(ScanRun.id.desc())
                .first()
            )
            return {"status": "already_running", "run_id": row.id if row else None}
    run_id = None
    try:
        with SessionLocal() as db:
            _fail_orphans(db)
            run = ScanRun(
                status="running", error_message="Scan admitted; preparing inventory"
            )
            db.add(run)
            db.commit()
            db.refresh(run)
            run_id = run.id

        def execute():
            try:
                with SessionLocal() as local_db:
                    run_full_scan(local_db, run_id=run_id, lease=lease)
            except Exception:
                logger.exception("Inventory scan failed: run_id=%s", run_id)
            finally:
                lease.close()

        thread = threading.Thread(
            target=execute, name=f"inventory-scan-{run_id}", daemon=True
        )
        thread.start()
        return {"status": "started", "run_id": run_id}
    except Exception:
        try:
            if run_id:
                with SessionLocal() as db:
                    row = db.get(ScanRun, run_id)
                    row.status = "failed"
                    row.finished_at = datetime.now(UTC)
                    row.error_message = (
                        "Scan admission failed before the worker started"
                    )
                    db.commit()
        finally:
            lease.close()
        raise

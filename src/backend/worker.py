"""Celery worker bootstrap for async job execution."""

import os
import csv
import json
from datetime import UTC, datetime
import uuid
from pathlib import Path
from celery import Celery
from sqlalchemy.orm import Session

from core.database import SessionLocal
from core.models import JobRun, LogEvent, OciDiagnostics, Setting
from core.redis_cache import cache_set
from services.aggregate_engine import refresh_aggregates, refresh_snapshot
from services.oci_client import OCIClientService
from services.oci_diagnostics import compute_status
from services.event_logger import audit_event, log_event, redact_sensitive


broker_url = os.getenv("CELERY_BROKER_URL", os.getenv("REDIS_URL", "redis://redis:6379/1"))
result_backend = os.getenv("CELERY_RESULT_BACKEND", os.getenv("REDIS_URL", "redis://redis:6379/2"))

celery_app = Celery("oci_cost_manager", broker=broker_url, backend=result_backend)
celery_app.conf.update(
    task_default_queue="default",
    task_track_started=True,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    worker_prefetch_multiplier=1,
    task_acks_late=True,
)


@celery_app.task(name="worker.health_ping")
def health_ping() -> dict:
    """Simple task used to validate worker connectivity."""
    return {"ok": True}


def _set_job_state(
    db: Session,
    job_id: str,
    *,
    status: str | None = None,
    progress: int | None = None,
    result: dict | None = None,
    error_message: str | None = None,
) -> None:
    job = db.query(JobRun).filter(JobRun.id == job_id).first()
    if not job:
        return
    if status is not None:
        job.status = status
    if progress is not None:
        job.progress = progress
    if result is not None:
        job.result = result
    if error_message is not None:
        job.error_message = error_message
    if status == "running" and not job.started_at:
        job.started_at = datetime.now(UTC)
    if status in {"succeeded", "failed"}:
        job.finished_at = datetime.now(UTC)
    db.commit()
    corr = None
    if isinstance(job.params, dict):
        corr = job.params.get("correlation_id")
    log_event(
        level="error" if status == "failed" else "info",
        log_type="backend",
        source="worker",
        message=f"job_state:{status or 'updated'}",
        correlation_id=corr or job_id,
        job_id=job_id,
        details={"job_type": job.job_type, "progress": job.progress, "error_message": job.error_message},
    )


@celery_app.task(name="jobs.aggregate_refresh")
def aggregate_refresh(job_id: str, params: dict | None = None) -> dict:
    db = SessionLocal()
    try:
        _set_job_state(db, job_id, status="running", progress=5)
        result = refresh_aggregates(db, params=params or {})
        _set_job_state(db, job_id, status="succeeded", progress=100, result=result)
        return result
    except Exception as exc:
        db.rollback()
        _set_job_state(db, job_id, status="failed", progress=100, error_message=str(exc))
        raise
    finally:
        db.close()


@celery_app.task(name="jobs.snapshot_refresh")
def snapshot_refresh(job_id: str, params: dict | None = None) -> dict:
    db = SessionLocal()
    try:
        _set_job_state(db, job_id, status="running", progress=10)
        result = refresh_snapshot(db, params=params or {})
        _set_job_state(db, job_id, status="succeeded", progress=100, result=result)
        return result
    except Exception as exc:
        db.rollback()
        _set_job_state(db, job_id, status="failed", progress=100, error_message=str(exc))
        raise
    finally:
        db.close()


def _safe_error(exc: Exception, service: str, op: str) -> dict:
    return {"code": type(exc).__name__, "message": str(exc), "service": service, "op": op}


def _check_config_and_key(db: Session) -> tuple[bool, bool, str | None, str | None, dict]:
    s = db.query(Setting).filter(Setting.id == 1).one_or_none()
    if not s:
        return False, False, None, None, {"code": "SettingsMissing", "message": "Settings row not found", "service": "config", "op": "load"}
    config_file = (getattr(s, "oci_config_file", None) or os.getenv("OCI_CONFIG_FILE") or "/home/app/.oci/config")
    key_file = getattr(s, "oci_key_file", None)
    key_content = getattr(s, "oci_key_content", None)
    config_detected = Path(str(config_file)).expanduser().exists() or bool(getattr(s, "oci_user", None))
    key_readable = bool((key_content or "").strip())
    if not key_readable and key_file:
        try:
            p = Path(str(key_file)).expanduser()
            key_readable = p.exists() and p.is_file() and p.stat().st_size > 0
        except Exception:
            key_readable = False
    return config_detected, key_readable, config_file, key_file, {}


@celery_app.task(name="jobs.diagnostics_refresh")
def diagnostics_refresh(job_id: str, params: dict | None = None) -> dict:
    db = SessionLocal()
    try:
        _set_job_state(db, job_id, status="running", progress=5)
        config_detected, key_readable, _config_file, _key_file, config_error = _check_config_and_key(db)
        errors: list[dict] = []
        if config_error:
            errors.append(config_error)

        tenancy_reachable = False
        identity_api_reachable = False
        usage_api_reachable = False
        cost_api_reachable = False
        regions: list[str] = []
        tenancy_ocid = None
        user_ocid = None
        fingerprint = None

        if config_detected and key_readable:
            try:
                client = OCIClientService()
                cfg = client.config
                tenancy_ocid = cfg.get("tenancy")
                user_ocid = cfg.get("user")
                fingerprint = cfg.get("fingerprint")
                regions = [cfg.get("region")] if cfg.get("region") else []
                _set_job_state(db, job_id, progress=30)

                try:
                    tenancy = client.identity_client.get_tenancy(client.tenancy_id).data
                    tenancy_reachable = bool(tenancy and getattr(tenancy, "id", None))
                    identity_api_reachable = True
                except Exception as exc:
                    errors.append(_safe_error(exc, "identity", "get_tenancy"))

                _set_job_state(db, job_id, progress=60)
                try:
                    # Minimal usage API check with bounded request object.
                    from datetime import timedelta
                    import oci
                    end_time = datetime.now(UTC)
                    start_time = end_time - timedelta(days=1)
                    req = oci.usage_api.models.RequestSummarizedUsagesDetails(
                        tenant_id=client.tenancy_id,
                        time_usage_started=start_time,
                        time_usage_ended=end_time,
                        granularity="DAILY",
                        group_by=["service"],
                    )
                    client.usage_client.request_summarized_usages(req)
                    usage_api_reachable = True
                    cost_api_reachable = True
                except Exception as exc:
                    errors.append(_safe_error(exc, "usage_api", "request_summarized_usages"))
            except Exception as exc:
                errors.append(_safe_error(exc, "oci_client", "init"))

        checks = {
            "config_detected": bool(config_detected),
            "key_readable": bool(key_readable),
            "tenancy_reachable": bool(tenancy_reachable),
            "identity_api_reachable": bool(identity_api_reachable),
            "usage_api_reachable": bool(usage_api_reachable),
            "cost_api_reachable": bool(cost_api_reachable),
        }
        status = compute_status({"checks": checks})
        message = "Diagnostics refresh completed"
        if errors:
            message = "Diagnostics completed with failures"
        last_sync = datetime.now(UTC)

        params = params or {}
        corr = params.get("correlation_id") or job_id
        row = OciDiagnostics(
            id=str(uuid.uuid4()),
            status=status,
            config_detected=checks["config_detected"],
            key_readable=checks["key_readable"],
            tenancy_reachable=checks["tenancy_reachable"],
            identity_api_reachable=checks["identity_api_reachable"],
            usage_api_reachable=checks["usage_api_reachable"],
            cost_api_reachable=checks["cost_api_reachable"],
            regions=regions,
            tenancy_ocid=tenancy_ocid,
            user_ocid=user_ocid,
            fingerprint=fingerprint,
            last_sync_time=last_sync,
            checked_at=datetime.now(UTC),
            message=message,
            error={"items": errors} if errors else {},
            correlation_id=corr,
        )
        db.add(row)
        db.commit()

        payload = {
            "status": status,
            "checks": checks,
            "last_sync_time": last_sync.isoformat(),
            "checked_at": row.checked_at.isoformat() if row.checked_at else datetime.now(UTC).isoformat(),
            "message": message,
            "mode": status,
            "error": row.error or {},
        }
        cache_set("diag:oci:latest", payload, 300)
        _set_job_state(db, job_id, status="succeeded", progress=100, result=payload)
        log_event(
            level="info",
            log_type="oci",
            source="worker",
            message="diagnostics_refresh_completed",
            correlation_id=corr,
            job_id=job_id,
            details={"status": status, "errors_count": len(errors)},
        )
        return payload
    except Exception as exc:
        db.rollback()
        _set_job_state(db, job_id, status="failed", progress=100, error_message=str(exc))
        log_event(
            level="error",
            log_type="oci",
            source="worker",
            message="diagnostics_refresh_failed",
            correlation_id=(params or {}).get("correlation_id") if isinstance(params, dict) else job_id,
            job_id=job_id,
            details={"error": str(exc)},
        )
        raise
    finally:
        db.close()


@celery_app.task(name="jobs.logs_export")
def logs_export(job_id: str, params: dict | None = None) -> dict:
    db = SessionLocal()
    try:
        params = params or {}
        corr = params.get("correlation_id") or job_id
        _set_job_state(db, job_id, status="running", progress=10)

        q = db.query(LogEvent)
        if params.get("log_type"):
            q = q.filter(LogEvent.log_type == params["log_type"])
        if params.get("level"):
            q = q.filter(LogEvent.level == params["level"])
        if params.get("correlation_id"):
            q = q.filter(LogEvent.correlation_id == params["correlation_id"])
        if params.get("job_id"):
            q = q.filter(LogEvent.job_id == params["job_id"])
        if params.get("q"):
            like = f"%{params['q']}%"
            q = q.filter(LogEvent.message.ilike(like))
        limit = int(params.get("limit") or 1000)
        rows = q.order_by(LogEvent.ts.desc()).limit(min(max(limit, 1), 5000)).all()
        _set_job_state(db, job_id, progress=70)

        export_dir = Path(os.getenv("EXPORT_DIR", "/exports"))
        export_dir.mkdir(parents=True, exist_ok=True)
        fmt = (params.get("format") or "json").lower()
        artifact = export_dir / f"logs_export_{job_id}.{fmt}"
        serialized = [
            {
                "id": r.id,
                "ts": r.ts.isoformat() if r.ts else None,
                "level": r.level,
                "log_type": r.log_type,
                "source": r.source,
                "actor": r.actor,
                "route": r.route,
                "method": r.method,
                "status_code": r.status_code,
                "correlation_id": r.correlation_id,
                "job_id": r.job_id,
                "message": r.message,
                "details": redact_sensitive(r.details or {}),
            }
            for r in rows
        ]
        if fmt == "csv":
            fields = ["id", "ts", "level", "log_type", "source", "actor", "route", "method", "status_code", "correlation_id", "job_id", "message", "details"]
            with artifact.open("w", newline="", encoding="utf-8") as fh:
                writer = csv.DictWriter(fh, fieldnames=fields)
                writer.writeheader()
                for item in serialized:
                    row = dict(item)
                    row["details"] = json.dumps(row.get("details") or {}, default=str)
                    writer.writerow(row)
        else:
            with artifact.open("w", encoding="utf-8") as fh:
                json.dump(serialized, fh, default=str)

        result = {"artifact": str(artifact), "format": fmt, "rows": len(serialized)}
        _set_job_state(db, job_id, status="succeeded", progress=100, result=result)
        audit_event(actor="worker", action="report_generate", target="logs_export", correlation_id=corr, meta=result)
        return result
    except Exception as exc:
        db.rollback()
        _set_job_state(db, job_id, status="failed", progress=100, error_message=str(exc))
        raise
    finally:
        db.close()

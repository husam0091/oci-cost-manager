"""Async job trigger/status endpoints for aggregate and snapshot refresh."""

from __future__ import annotations

from datetime import UTC, datetime
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core.database import get_db
from core.models import JobRun
from services.event_logger import audit_event, log_event
from worker import celery_app

router = APIRouter()

ALLOWED_JOB_TYPES = {"aggregate_refresh", "snapshot_refresh", "diagnostics_refresh", "logs_export"}


class JobCreateRequest(BaseModel):
    params: dict = Field(default_factory=dict)


def _create_job(db: Session, job_type: str, params: dict) -> JobRun:
    job = JobRun(
        id=str(uuid.uuid4()),
        job_type=job_type,
        status="queued",
        progress=0,
        params=params or {},
        created_at=datetime.now(UTC),
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


@router.post("/diagnostics_refresh", status_code=status.HTTP_202_ACCEPTED)
async def create_diagnostics_refresh_job(body: JobCreateRequest, request: Request, db: Session = Depends(get_db)):
    corr = request.headers.get("x-correlation-id") or str(uuid.uuid4())
    params = {**(body.params or {}), "correlation_id": corr}
    job = _create_job(db, "diagnostics_refresh", params)
    celery_app.send_task("jobs.diagnostics_refresh", args=[job.id, params], queue="heavy")
    log_event(level="info", log_type="backend", source="api", message="job_triggered", correlation_id=corr, job_id=job.id, details={"job_type": "diagnostics_refresh"})
    audit_event(actor=request.headers.get("x-user") or "anonymous", action="job_trigger", target="diagnostics_refresh", correlation_id=corr, meta={"job_id": job.id})
    return {"success": True, "data": {"job_id": job.id, "status": "queued"}}


@router.post("/{job_type}", status_code=status.HTTP_202_ACCEPTED)
async def create_job(job_type: str, body: JobCreateRequest, request: Request, db: Session = Depends(get_db)):
    if job_type not in ALLOWED_JOB_TYPES:
        raise HTTPException(status_code=404, detail="Unsupported job type")
    corr = request.headers.get("x-correlation-id") or str(uuid.uuid4())
    params = {**(body.params or {}), "correlation_id": corr}
    job = _create_job(db, job_type, params)
    task_name = f"jobs.{job_type}"
    celery_app.send_task(task_name, args=[job.id, params], queue="heavy")
    log_event(level="info", log_type="backend", source="api", message="job_triggered", correlation_id=corr, job_id=job.id, details={"job_type": job_type})
    audit_event(actor=request.headers.get("x-user") or "anonymous", action="job_trigger", target=job_type, correlation_id=corr, meta={"job_id": job.id})
    return {"success": True, "data": {"job_id": job.id, "status": "queued"}}


@router.get("/summary")
async def get_jobs_summary(db: Session = Depends(get_db)):
    rows = db.query(JobRun).all()
    status_counts: dict[str, int] = {}
    worker_busy = False
    reports_running = False
    for row in rows:
        status_counts[row.status] = status_counts.get(row.status, 0) + 1
        if row.status in {"queued", "running"}:
            worker_busy = True
        if str(row.job_type or "").startswith("report") and row.status in {"queued", "running"}:
            reports_running = True
    worker_state = "busy" if worker_busy else "idle"
    report_state = "running" if reports_running else "ready"
    if status_counts.get("failed", 0) > 0 and status_counts.get("running", 0) == 0:
        worker_state = "error"
    return {
        "success": True,
        "data": {
            "status_counts": status_counts,
            "worker_state": worker_state,
            "report_state": report_state,
        },
    }


@router.get("/{job_id}")
async def get_job(job_id: str, db: Session = Depends(get_db)):
    job = db.query(JobRun).filter(JobRun.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {
        "success": True,
        "data": {
            "job_id": job.id,
            "job_type": job.job_type,
            "status": job.status,
            "progress": job.progress,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "finished_at": job.finished_at.isoformat() if job.finished_at else None,
            "error_message": job.error_message,
        },
    }


@router.get("/{job_id}/result")
async def get_job_result(job_id: str, db: Session = Depends(get_db)):
    job = db.query(JobRun).filter(JobRun.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {
        "success": True,
        "data": {
            "job_id": job.id,
            "status": job.status,
            "result": job.result or {},
        },
    }

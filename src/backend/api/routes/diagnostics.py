"""Phase 4 diagnostics endpoints (cache-first, non-blocking)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core.database import get_db
from core.models import JobRun
from services.event_logger import audit_event, log_event
from services.oci_diagnostics import get_diagnostics_response
from worker import celery_app

import uuid
from datetime import UTC, datetime

router = APIRouter()


class DiagnosticsJobRequest(BaseModel):
    params: dict = Field(default_factory=dict)


@router.get("")
async def get_diagnostics(request: Request, db: Session = Depends(get_db)):
    data, source = get_diagnostics_response(db)
    corr = request.headers.get("x-correlation-id") or str(uuid.uuid4())
    log_event(level="info", log_type="backend", source="api", message="diagnostics_read", correlation_id=corr, details={"source": source, "status": data.get("status")})
    return {"success": True, "data": data, "meta": {"source": source}}


@router.post("/refresh", status_code=status.HTTP_202_ACCEPTED)
async def refresh_diagnostics(body: DiagnosticsJobRequest, request: Request, db: Session = Depends(get_db)):
    corr = request.headers.get("x-correlation-id") or str(uuid.uuid4())
    params = {**(body.params or {}), "correlation_id": corr}
    job = JobRun(
        id=str(uuid.uuid4()),
        job_type="diagnostics_refresh",
        status="queued",
        progress=0,
        params=params,
        created_at=datetime.now(UTC),
    )
    db.add(job)
    db.commit()
    celery_app.send_task("jobs.diagnostics_refresh", args=[job.id, params], queue="heavy")
    log_event(level="info", log_type="backend", source="api", message="diagnostics_refresh_triggered", correlation_id=corr, job_id=job.id)
    audit_event(actor=request.headers.get("x-user") or "anonymous", action="job_trigger", target="diagnostics_refresh", correlation_id=corr, meta={"job_id": job.id})
    return {"success": True, "data": {"job_id": job.id, "status": "queued"}}

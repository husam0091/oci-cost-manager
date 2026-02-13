"""Phase 5 logs API: query, correlation timeline, frontend telemetry, async export."""

from __future__ import annotations

import csv
import json
import os
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import and_, desc, or_
from sqlalchemy.orm import Session

from core.database import get_db
from core.models import AuditEvent, JobRun, LogEvent
from services.event_logger import audit_event, log_event, redact_sensitive
from worker import celery_app

router = APIRouter()

ALLOWED_LOG_TYPES = {"oci", "backend", "frontend", "db", "security", "audit"}
ALLOWED_LEVELS = {"debug", "info", "warn", "error", "critical"}


class FrontendLogIn(BaseModel):
    level: str = Field(default="info")
    message: str
    route: str | None = None
    correlation_id: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class LogsExportRequest(BaseModel):
    format: str = Field(default="json")
    log_type: str | None = None
    level: str | None = None
    q: str | None = None
    correlation_id: str | None = None
    job_id: str | None = None
    from_ts: str | None = Field(default=None, alias="from")
    to_ts: str | None = Field(default=None, alias="to")
    limit: int = 1000

    class Config:
        populate_by_name = True


def _request_actor(request: Request) -> str:
    return request.headers.get("x-user") or request.cookies.get("username") or "anonymous"


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


def _serialize_log(row: LogEvent) -> dict[str, Any]:
    return {
        "id": row.id,
        "ts": row.ts.isoformat() if row.ts else None,
        "level": row.level,
        "log_type": row.log_type,
        "source": row.source,
        "actor": row.actor,
        "route": row.route,
        "method": row.method,
        "status_code": row.status_code,
        "correlation_id": row.correlation_id,
        "request_id": row.request_id,
        "job_id": row.job_id,
        "resource_ocid": row.resource_ocid,
        "compartment_ocid": row.compartment_ocid,
        "service": row.service,
        "message": row.message,
        "details": row.details or {},
    }


@router.post("/frontend")
async def ingest_frontend_log(payload: FrontendLogIn, request: Request):
    correlation_id = payload.correlation_id or request.headers.get("x-correlation-id") or str(uuid.uuid4())
    level = payload.level.lower() if payload.level else "info"
    if level not in ALLOWED_LEVELS:
        level = "info"
    log_event(
        level=level,
        log_type="frontend",
        source="frontend",
        message=payload.message[:2000],
        actor=_request_actor(request),
        route=payload.route,
        correlation_id=correlation_id,
        details=payload.details or {},
    )
    return {"success": True}


@router.get("")
async def list_logs(
    request: Request,
    db: Session = Depends(get_db),
    log_type: str | None = None,
    level: str | None = None,
    q: str | None = None,
    correlation_id: str | None = None,
    job_id: str | None = None,
    from_ts: str | None = Query(default=None, alias="from"),
    to_ts: str | None = Query(default=None, alias="to"),
    limit: int = Query(default=200, ge=1, le=1000),
):
    filters = []
    if log_type:
        filters.append(LogEvent.log_type == log_type)
    if level:
        filters.append(LogEvent.level == level)
    if correlation_id:
        filters.append(LogEvent.correlation_id == correlation_id)
    if job_id:
        filters.append(LogEvent.job_id == job_id)
    if q:
        like = f"%{q}%"
        filters.append(or_(LogEvent.message.ilike(like), LogEvent.route.ilike(like), LogEvent.source.ilike(like)))
    f = _parse_iso(from_ts)
    t = _parse_iso(to_ts)
    if f:
        filters.append(LogEvent.ts >= f)
    if t:
        filters.append(LogEvent.ts <= t)

    query = db.query(LogEvent)
    if filters:
        query = query.filter(and_(*filters))
    rows = query.order_by(desc(LogEvent.ts)).limit(limit).all()
    items = [_serialize_log(r) for r in rows]
    return {"success": True, "data": {"items": items, "count": len(items)}}


def _get_timeline(correlation_id: str, db: Session) -> dict[str, Any]:
    log_rows = (
        db.query(LogEvent)
        .filter(LogEvent.correlation_id == correlation_id)
        .order_by(desc(LogEvent.ts))
        .all()
    )
    audit_rows = (
        db.query(AuditEvent)
        .filter(AuditEvent.correlation_id == correlation_id)
        .order_by(desc(AuditEvent.ts))
        .all()
    )
    timeline = [_serialize_log(r) for r in log_rows]
    for a in audit_rows:
        timeline.append(
            {
                "id": a.id,
                "ts": a.ts.isoformat() if a.ts else None,
                "level": "info",
                "log_type": "audit",
                "source": "api",
                "actor": a.actor,
                "message": a.action,
                "correlation_id": a.correlation_id,
                "details": a.meta or {},
            }
        )
    timeline.sort(key=lambda x: x.get("ts") or "", reverse=True)
    return {"success": True, "data": {"correlation_id": correlation_id, "items": timeline}}


@router.post("/export", status_code=status.HTTP_202_ACCEPTED)
async def export_logs(payload: LogsExportRequest, request: Request, db: Session = Depends(get_db)):
    correlation_id = request.headers.get("x-correlation-id") or str(uuid.uuid4())
    fmt = (payload.format or "json").lower()
    if fmt not in {"json", "csv"}:
        raise HTTPException(status_code=400, detail="format must be json or csv")
    job = JobRun(
        id=str(uuid.uuid4()),
        job_type="logs_export",
        status="queued",
        progress=0,
        params=redact_sensitive(payload.model_dump(by_alias=True)),
        created_at=datetime.now(UTC),
    )
    db.add(job)
    db.commit()
    celery_app.send_task("jobs.logs_export", args=[job.id, payload.model_dump(by_alias=True)], queue="heavy")
    audit_event(
        actor=_request_actor(request),
        action="report_generate",
        target="logs_export",
        correlation_id=correlation_id,
        meta={"job_id": job.id, "format": fmt},
    )
    return {"success": True, "data": {"job_id": job.id, "status": "queued"}}


@router.get("/metrics/db")
async def db_metrics():
    database_url = os.getenv("DATABASE_URL", "")
    return {
        "success": True,
        "data": {
            "backend_store": "postgres" if database_url.startswith("postgresql") else "sqlite",
            "database_url_driver": database_url.split("://", 1)[0] if "://" in database_url else "unknown",
            "pgbouncer_hosted": "pgbouncer" in database_url,
            "ts": datetime.now(UTC).isoformat(),
        },
    }


@router.get("/{correlation_id}")
async def correlation_timeline(correlation_id: str, db: Session = Depends(get_db)):
    return _get_timeline(correlation_id, db)

"""Secure OCI settings routes (Phase 1)."""

from __future__ import annotations

from collections import defaultdict, deque
from datetime import UTC, datetime, timedelta
import uuid
from typing import Optional

from fastapi import APIRouter, Cookie, Depends, File, HTTPException, Request, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from core.auth import decode_token
from core.database import get_db
from core.models import OciIntegration, Setting
from core.rbac import resolve_principal
from services.event_logger import audit_event
from services.oci_client import test_oci_connection
from services.oci_credentials import get_oci_runtime_credentials, rotate_oci_private_key, upsert_oci_metadata

router = APIRouter()

_RATE_WINDOW = timedelta(minutes=1)
_RATE_LIMIT = 5
_TEST_RATE: dict[str, deque[datetime]] = defaultdict(deque)
# TODO: Replace with Redis-based limiter for multi-instance deployments.


class OciMetadataRequest(BaseModel):
    user_ocid: str
    tenancy_ocid: str
    fingerprint: str
    region: str


def _require_admin(
    token: Optional[str] = Cookie(default=None, alias="access_token"),
    db: Session = Depends(get_db),
):
    try:
        principal = resolve_principal(db, token, strict=True)
    except PermissionError:
        raise HTTPException(status_code=401, detail="Not authenticated")
    if principal.role != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")
    return {"sub": principal.username}


def _rate_limit(user_key: str) -> None:
    now = datetime.now(UTC)
    q = _TEST_RATE[user_key]
    while q and (now - q[0]) > _RATE_WINDOW:
        q.popleft()
    if len(q) >= _RATE_LIMIT:
        raise HTTPException(status_code=429, detail={"success": False, "error": {"code": "RATE_LIMITED", "reason": "Too many test requests"}})
    q.append(now)


@router.post("/settings/oci")
async def save_oci_settings(req: OciMetadataRequest, request: Request, db: Session = Depends(get_db), user=Depends(_require_admin)):
    actor = user.get("sub") or "admin"
    row = upsert_oci_metadata(
        db,
        user_ocid=req.user_ocid,
        tenancy_ocid=req.tenancy_ocid,
        fingerprint=req.fingerprint,
        region=req.region,
        actor=actor,
    )
    corr = getattr(request.state, "correlation_id", None) or str(uuid.uuid4())
    audit_event(
        actor=actor,
        action="oci_settings_saved",
        target="oci_settings",
        correlation_id=corr,
        meta={"ip": request.client.host if request.client else None, "result": "ok"},
    )
    return {
        "success": True,
        "data": {
            "configured": True,
            "fingerprint": row.fingerprint,
            "region": row.region,
            "last_test_status": row.status,
            "last_tested_at": row.last_tested_at.isoformat() if row.last_tested_at else None,
        },
    }


@router.post("/settings/oci/key")
async def rotate_oci_key(request: Request, key_file: UploadFile = File(...), db: Session = Depends(get_db), user=Depends(_require_admin)):
    if not key_file.filename.lower().endswith(".pem"):
        raise HTTPException(status_code=400, detail={"success": False, "error": {"code": "INVALID_FILE_TYPE", "reason": "Only .pem is accepted"}})
    content = (await key_file.read()).decode("utf-8", errors="ignore")
    row = rotate_oci_private_key(db, pem_text=content)
    integration = db.query(OciIntegration).order_by(OciIntegration.id.desc()).first()
    if integration:
        integration.rotated_at = datetime.now(UTC)
        integration.updated_by = user.get("sub") or "admin"
        db.commit()
    corr = getattr(request.state, "correlation_id", None) or str(uuid.uuid4())
    audit_event(
        actor=user.get("sub") or "admin",
        action="oci_key_rotated",
        target="oci_settings",
        correlation_id=corr,
        meta={"ip": request.client.host if request.client else None, "result": "ok"},
    )
    return {"success": True, "data": {"rotated_at": row.rotated_at.isoformat() if row.rotated_at else None}}


@router.post("/settings/oci/test")
async def test_oci_settings(request: Request, db: Session = Depends(get_db), user=Depends(_require_admin)):
    user_key = user.get("sub") or "admin"
    _rate_limit(user_key)
    row = db.query(OciIntegration).order_by(OciIntegration.id.desc()).first()
    corr = getattr(request.state, "correlation_id", None) or str(uuid.uuid4())
    now = datetime.now(UTC)
    try:
        runtime = get_oci_runtime_credentials(db)
        if not runtime.get("key_content"):
            raise RuntimeError("OCI key missing")
        data = test_oci_connection(runtime)
        if row:
            row.status = "healthy"
            row.last_tested_at = now
            db.commit()
        audit_event(
            actor=user_key,
            action="oci_test_run",
            target="oci_settings",
            correlation_id=corr,
            meta={"ip": request.client.host if request.client else None, "result": "ok"},
        )
        return {
            "success": True,
            "data": {
                "status": "healthy",
                "configured": True,
                "tenancy_name": data.get("tenancy_name"),
                "region": data.get("region"),
            },
        }
    except Exception as _exc:
        import traceback as _tb
        _reason = f"{type(_exc).__name__}: {_exc}"
        _trace = _tb.format_exc()
        import logging as _log
        _log.getLogger(__name__).error("OCI test failed: %s\n%s", _reason, _trace)
        if row:
            row.status = "failed"
            row.last_tested_at = now
            db.commit()
        audit_event(
            actor=user_key,
            action="oci_test_run",
            target="oci_settings",
            correlation_id=corr,
            meta={"ip": request.client.host if request.client else None, "result": "failed"},
        )
        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "error": {
                    "code": "OCI_TEST_FAILED",
                    "reason": _reason,
                    "correlation_id": corr,
                },
            },
        )

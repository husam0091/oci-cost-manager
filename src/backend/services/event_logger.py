"""Structured event/audit logging with safe redaction and DB fallback."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.exc import SQLAlchemyError

from core.database import SessionLocal
from core.models import AuditEvent, LogEvent

logger = logging.getLogger("oci-cost-manager")

_SENSITIVE_KEYS = {
    "password",
    "passphrase",
    "token",
    "secret",
    "authorization",
    "private_key",
    "oci_key_content",
    "key_content",
    "api_key",
}


def redact_sensitive(value: Any) -> Any:
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for k, v in value.items():
            if str(k).lower() in _SENSITIVE_KEYS:
                redacted[k] = "***REDACTED***"
            else:
                redacted[k] = redact_sensitive(v)
        return redacted
    if isinstance(value, list):
        return [redact_sensitive(v) for v in value]
    return value


def _stdout_fallback(payload: dict[str, Any]) -> None:
    try:
        logger.warning(json.dumps(payload, default=str))
    except Exception:
        logger.warning("log_event_fallback_failed")


def log_event(
    *,
    level: str,
    log_type: str,
    source: str,
    message: str,
    actor: str | None = None,
    route: str | None = None,
    method: str | None = None,
    status_code: int | None = None,
    correlation_id: str | None = None,
    request_id: str | None = None,
    job_id: str | None = None,
    resource_ocid: str | None = None,
    compartment_ocid: str | None = None,
    service: str | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    payload = {
        "id": str(uuid.uuid4()),
        "ts": datetime.now(UTC),
        "level": (level or "info").lower(),
        "log_type": log_type,
        "source": source,
        "actor": actor,
        "route": route,
        "method": method,
        "status_code": status_code,
        "correlation_id": correlation_id or str(uuid.uuid4()),
        "request_id": request_id,
        "job_id": job_id,
        "resource_ocid": resource_ocid,
        "compartment_ocid": compartment_ocid,
        "service": service,
        "message": message,
        "details": redact_sensitive(details or {}),
    }
    db = None
    try:
        db = SessionLocal()
        db.add(LogEvent(**payload))
        db.commit()
    except SQLAlchemyError:
        _stdout_fallback(payload)
        if db is not None:
            db.rollback()
    except Exception:
        _stdout_fallback(payload)
        if db is not None:
            db.rollback()
    finally:
        if db is not None:
            db.close()


def audit_event(
    *,
    actor: str,
    action: str,
    correlation_id: str,
    target: str | None = None,
    meta: dict[str, Any] | None = None,
) -> None:
    payload = {
        "id": str(uuid.uuid4()),
        "ts": datetime.now(UTC),
        "actor": actor or "unknown",
        "action": action,
        "target": target,
        "correlation_id": correlation_id,
        "meta": redact_sensitive(meta or {}),
    }
    db = None
    try:
        db = SessionLocal()
        db.add(AuditEvent(**payload))
        db.commit()
    except Exception:
        if db is not None:
            db.rollback()
        _stdout_fallback({"event": "audit_fallback", **payload})
    finally:
        if db is not None:
            db.close()

    log_event(
        level="info",
        log_type="audit",
        source="api",
        message=f"audit:{action}",
        actor=actor,
        correlation_id=correlation_id,
        details={"target": target, "meta": meta or {}},
    )

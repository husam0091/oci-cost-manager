"""OCI diagnostics cache-first service with safe fallbacks."""

from __future__ import annotations

import asyncio
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from time import perf_counter
from typing import Any, Callable

from sqlalchemy import desc
from sqlalchemy.orm import Session

from core.models import CostSnapshot, OciDiagnostics
from core.redis_cache import cache_get, cache_set

DIAG_CACHE_KEY = "diag:oci:latest"
DIAG_CACHE_TTL_SECONDS = 300


def _minimal_unknown(message: str = "Diagnostics unavailable") -> dict[str, Any]:
    return {
        "status": "degraded",
        "checks": {
            "config_detected": False,
            "key_readable": False,
            "tenancy_reachable": False,
            "identity_api_reachable": False,
            "usage_api_reachable": False,
            "cost_api_reachable": False,
        },
        "last_sync_time": None,
        "checked_at": datetime.now(UTC).isoformat(),
        "message": message,
        "mode": "degraded",
    }


def cache_get_diagnostics() -> dict[str, Any] | None:
    data = cache_get(DIAG_CACHE_KEY)
    return data if isinstance(data, dict) else None


def cache_set_diagnostics(data: dict[str, Any], ttl: int = DIAG_CACHE_TTL_SECONDS) -> None:
    cache_set(DIAG_CACHE_KEY, data, ttl)


def _snapshot_last_sync(db: Session) -> datetime | None:
    try:
        row = (
            db.query(CostSnapshot)
            .order_by(desc(CostSnapshot.computed_at), desc(CostSnapshot.end_date), desc(CostSnapshot.created_at))
            .first()
        )
        if not row:
            return None
        return row.computed_at or row.end_date or row.created_at
    except Exception:
        return None


def read_latest_diagnostics(db: Session) -> dict[str, Any] | None:
    try:
        row = db.query(OciDiagnostics).order_by(desc(OciDiagnostics.checked_at)).first()
    except Exception:
        return None
    if not row:
        return None
    checks = {
        "config_detected": bool(row.config_detected),
        "key_readable": bool(row.key_readable),
        "tenancy_reachable": bool(row.tenancy_reachable),
        "identity_api_reachable": bool(row.identity_api_reachable),
        "usage_api_reachable": bool(row.usage_api_reachable),
        "cost_api_reachable": bool(row.cost_api_reachable),
    }
    return {
        "status": row.status,
        "checks": checks,
        "last_sync_time": row.last_sync_time.isoformat() if row.last_sync_time else None,
        "checked_at": row.checked_at.isoformat() if row.checked_at else None,
        "message": row.message or "Using stored diagnostics",
        "mode": row.status or "degraded",
        "error": row.error or {},
    }


def compute_status(model: dict[str, Any]) -> str:
    checks = model.get("checks", {})
    config_ok = bool(checks.get("config_detected"))
    key_ok = bool(checks.get("key_readable"))
    tenancy_ok = bool(checks.get("tenancy_reachable"))
    identity_ok = bool(checks.get("identity_api_reachable"))
    usage_ok = bool(checks.get("usage_api_reachable"))
    cost_ok = bool(checks.get("cost_api_reachable"))
    if not config_ok or not key_ok or not identity_ok:
        return "failed"
    if config_ok and key_ok and tenancy_ok and identity_ok and usage_ok and cost_ok:
        return "connected"
    return "partial"


async def safe_check(
    fn: Callable[[], Any],
    *,
    service: str,
    op: str,
    timeout_seconds: float = 35.0,
) -> dict[str, Any]:
    started = perf_counter()
    try:
        result = await asyncio.wait_for(asyncio.to_thread(fn), timeout=timeout_seconds)
        return {
            "ok": True,
            "duration_ms": int((perf_counter() - started) * 1000),
            "result": result,
            "error": None,
            "service": service,
            "op": op,
        }
    except Exception as exc:
        return {
            "ok": False,
            "duration_ms": int((perf_counter() - started) * 1000),
            "result": None,
            "error": {"code": type(exc).__name__, "message": str(exc), "service": service, "op": op},
            "service": service,
            "op": op,
        }


def config_detected(config_path: str | None) -> bool:
    if config_path and Path(config_path).expanduser().exists():
        return True
    return bool(os.getenv("OCI_CONFIG_FILE") or os.getenv("OCI_USER"))


def key_readable(key_file: str | None, key_content: str | None) -> bool:
    if key_content and str(key_content).strip():
        return True
    if not key_file:
        return False
    try:
        path = Path(key_file).expanduser()
        return path.exists() and path.is_file() and path.stat().st_size > 0
    except Exception:
        return False


def ensure_degraded_if_stale(data: dict[str, Any], db: Session, stale_hours: int = 24) -> dict[str, Any]:
    last_sync = _snapshot_last_sync(db)
    if not last_sync:
        data["status"] = "degraded"
        data["mode"] = "degraded"
        data["message"] = "Using last available snapshot"
        data["last_sync_time"] = None
        return data
    if last_sync.tzinfo is None:
        last_sync = last_sync.replace(tzinfo=UTC)
    data["last_sync_time"] = last_sync.isoformat()
    if datetime.now(UTC) - last_sync > timedelta(hours=stale_hours):
        data["status"] = "degraded"
        data["mode"] = "degraded"
        data["message"] = "Last sync is stale; using last available snapshot"
    return data


def get_diagnostics_response(db: Session) -> tuple[dict[str, Any], str]:
    cached = cache_get_diagnostics()
    if cached:
        return ensure_degraded_if_stale(cached, db), "cache"
    latest = read_latest_diagnostics(db)
    if latest:
        latest = ensure_degraded_if_stale(latest, db)
        cache_set_diagnostics(latest)
        return latest, "db"
    fallback = ensure_degraded_if_stale(_minimal_unknown("Using cached diagnostics"), db)
    return fallback, "unknown"

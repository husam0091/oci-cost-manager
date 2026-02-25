"""Health and readiness endpoints."""

from __future__ import annotations

from datetime import UTC, datetime
import time

from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from core.database import engine, init_db
from services import get_oci_client

router = APIRouter()


def _db_write_probe() -> tuple[bool, str]:
    try:
        probe_id = int(time.time())
        with engine.begin() as conn:
            conn.execute(text("CREATE TABLE IF NOT EXISTS __health_probe (id INTEGER PRIMARY KEY, ts TEXT NOT NULL)"))
            conn.execute(
                text("INSERT INTO __health_probe (id, ts) VALUES (:id, :ts)"),
                {"id": probe_id, "ts": datetime.now(UTC).isoformat()},
            )
            conn.execute(
                text(
                    "DELETE FROM __health_probe WHERE id NOT IN (SELECT id FROM __health_probe ORDER BY id DESC LIMIT 3)"
                )
            )
        return True, "ok"
    except Exception as exc:
        return False, str(exc)


@router.get("/health")
async def health_check():
    """Backward-compatible basic health check."""
    return {"status": "healthy"}


@router.get("/health/live")
async def liveness_check():
    """Lightweight liveness check for container/runtime probes."""
    return {"status": "alive"}


@router.get("/health/ready")
async def readiness_check():
    """Readiness check requiring schema ensure + writable DB."""
    try:
        init_db()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Initialization check failed: {str(exc)}")
    writable, reason = _db_write_probe()
    if not writable:
        raise HTTPException(status_code=503, detail=f"DB write probe failed: {reason}")
    return {"status": "ready", "checks": {"db_writable": True, "schema_ensure": True}}


@router.get("/health/oci")
async def oci_health_check():
    """Check OCI connection health."""
    try:
        oci_client = get_oci_client()
        tenancy = oci_client.get_tenancy()
        return {
            "status": "healthy",
            "tenancy_name": tenancy.name,
            "region": oci_client.region,
        }
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"OCI connection failed: {str(e)}",
        )

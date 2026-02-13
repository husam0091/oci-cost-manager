"""OCI tag update executor (thin wrapper with dry-run support)."""

from __future__ import annotations

from typing import Any


def execute(*, target_ref: dict[str, Any], proposed_change: dict[str, Any], dry_run: bool) -> dict[str, Any]:
    resource_id = target_ref.get("resource_id") or target_ref.get("ocid")
    tags = proposed_change.get("tags") or {}
    planned_call = {
        "service": "oci",
        "operation": "update_tags",
        "resource_id": resource_id,
        "tags": tags,
    }
    if dry_run:
        return {"ok": True, "dry_run": True, "planned_calls": [planned_call], "rollback_supported": True}
    return {"ok": True, "dry_run": False, "planned_calls": [planned_call], "rollback_supported": True, "message": "OCI tag update executed (simulated)."}


def rollback(*, target_ref: dict[str, Any], payload: dict[str, Any], dry_run: bool) -> dict[str, Any]:
    resource_id = target_ref.get("resource_id") or target_ref.get("ocid")
    previous_tags = payload.get("before_tags") or {}
    planned_call = {
        "service": "oci",
        "operation": "restore_tags",
        "resource_id": resource_id,
        "tags": previous_tags,
    }
    return {"ok": True, "dry_run": dry_run, "planned_calls": [planned_call], "message": "OCI tag rollback planned."}

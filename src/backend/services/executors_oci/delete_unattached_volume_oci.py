"""OCI volume deletion executor."""

from __future__ import annotations

from typing import Any


def execute(*, target_ref: dict[str, Any], dry_run: bool, confirm_delete: bool) -> dict[str, Any]:
    resource_id = target_ref.get("resource_id") or target_ref.get("ocid")
    planned_call = {"service": "oci", "operation": "volume_delete", "volume_id": resource_id}
    if not dry_run and not confirm_delete:
        return {"ok": False, "dry_run": False, "planned_calls": [planned_call], "message": "confirm_delete=true is required for OCI volume deletion."}
    return {
        "ok": True,
        "dry_run": dry_run,
        "planned_calls": [planned_call],
        "rollback_supported": False,
        "message": "OCI volume delete planned/executed.",
    }


def rollback(*_args, **_kwargs) -> dict[str, Any]:
    return {"ok": False, "message": "Rollback is not supported for OCI volume delete."}

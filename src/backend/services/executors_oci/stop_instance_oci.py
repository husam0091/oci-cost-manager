"""OCI stop/start instance executor."""

from __future__ import annotations

from typing import Any


def execute(*, target_ref: dict[str, Any], dry_run: bool) -> dict[str, Any]:
    resource_id = target_ref.get("resource_id") or target_ref.get("ocid")
    planned_call = {"service": "oci", "operation": "instance_stop", "instance_id": resource_id}
    return {"ok": True, "dry_run": dry_run, "planned_calls": [planned_call], "rollback_supported": True, "message": "OCI stop instance planned/executed."}


def rollback(*, target_ref: dict[str, Any], dry_run: bool) -> dict[str, Any]:
    resource_id = target_ref.get("resource_id") or target_ref.get("ocid")
    planned_call = {"service": "oci", "operation": "instance_start", "instance_id": resource_id}
    return {"ok": True, "dry_run": dry_run, "planned_calls": [planned_call], "message": "OCI start instance rollback planned/executed."}

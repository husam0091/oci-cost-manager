"""Stop idle instance executor."""

from __future__ import annotations

from typing import Any


def execute(*, target_ref: dict[str, Any], dry_run: bool) -> dict[str, Any]:
    target = target_ref.get("resource_id") or target_ref.get("ocid") or "unknown"
    if dry_run:
        return {
            "ok": True,
            "dry_run": True,
            "rollback_supported": True,
            "message": f"Dry-run: would stop instance {target}.",
        }
    return {
        "ok": True,
        "dry_run": False,
        "rollback_supported": True,
        "message": f"Executed stop_idle_instance for {target} (simulated).",
    }


def rollback(*, target_ref: dict[str, Any], dry_run: bool) -> dict[str, Any]:
    target = target_ref.get("resource_id") or target_ref.get("ocid") or "unknown"
    if dry_run:
        return {"ok": True, "dry_run": True, "message": f"Dry-run: would start instance {target}."}
    return {"ok": True, "dry_run": False, "message": f"Rollback executed: started instance {target} (simulated)."}

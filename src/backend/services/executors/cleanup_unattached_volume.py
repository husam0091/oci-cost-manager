"""Cleanup unattached volume executor."""

from __future__ import annotations

from typing import Any


def execute(*, target_ref: dict[str, Any], proposed_change: dict[str, Any], dry_run: bool, confirm_delete: bool) -> dict[str, Any]:
    target = target_ref.get("resource_id") or target_ref.get("ocid") or "unknown"
    if dry_run:
        return {
            "ok": True,
            "dry_run": True,
            "rollback_supported": False,
            "message": f"Dry-run: would delete unattached volume {target}.",
        }
    if not confirm_delete:
        return {
            "ok": False,
            "dry_run": False,
            "rollback_supported": False,
            "message": "Explicit confirm_delete=true is required for cleanup_unattached_volume.",
        }
    return {
        "ok": True,
        "dry_run": False,
        "rollback_supported": False,
        "message": f"Executed cleanup_unattached_volume for {target} (simulated).",
        "proposed_change": proposed_change,
    }


def rollback(*_args, **_kwargs) -> dict[str, Any]:
    return {"ok": False, "message": "Rollback is not supported for cleanup_unattached_volume."}

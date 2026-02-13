"""Tag fix executor."""

from __future__ import annotations

from typing import Any

from core.models import Resource


def execute(*, db, target_ref: dict[str, Any], proposed_change: dict[str, Any], dry_run: bool) -> dict[str, Any]:
    resource_id = target_ref.get("resource_id") or target_ref.get("ocid")
    if not resource_id:
        return {"ok": False, "message": "target_ref.resource_id is required for tag_fix.", "rollback_supported": True}

    resource = db.query(Resource).filter(Resource.ocid == resource_id).one_or_none()
    if not resource:
        return {"ok": False, "message": f"Resource {resource_id} not found.", "rollback_supported": True}

    details = resource.details or {}
    existing_tags = (details.get("freeform_tags") or {}).copy()
    desired_tags = (proposed_change.get("tags") or {}).copy()

    if dry_run:
        return {
            "ok": True,
            "dry_run": True,
            "rollback_supported": True,
            "message": f"Dry-run: would apply tags to {resource_id}.",
            "before_tags": existing_tags,
            "after_tags": {**existing_tags, **desired_tags},
        }

    merged = {**existing_tags, **desired_tags}
    details["freeform_tags"] = merged
    resource.details = details
    db.add(resource)
    return {
        "ok": True,
        "dry_run": False,
        "rollback_supported": True,
        "message": f"Applied tags to {resource_id}.",
        "before_tags": existing_tags,
        "after_tags": merged,
    }


def rollback(*, db, target_ref: dict[str, Any], payload: dict[str, Any], dry_run: bool) -> dict[str, Any]:
    resource_id = target_ref.get("resource_id") or target_ref.get("ocid")
    if not resource_id:
        return {"ok": False, "message": "target_ref.resource_id is required for rollback."}
    resource = db.query(Resource).filter(Resource.ocid == resource_id).one_or_none()
    if not resource:
        return {"ok": False, "message": f"Resource {resource_id} not found."}

    old_tags = payload.get("before_tags") or {}
    if dry_run:
        return {"ok": True, "dry_run": True, "message": f"Dry-run: would restore previous tags for {resource_id}."}

    details = resource.details or {}
    details["freeform_tags"] = old_tags
    resource.details = details
    db.add(resource)
    return {"ok": True, "dry_run": False, "message": f"Restored previous tags for {resource_id}."}

"""Notify-only executor (always safe)."""

from __future__ import annotations

from typing import Any

from services.notifications import send_notifications


def execute(*, payload: dict[str, Any], email_cfg: dict[str, Any], webhook_cfg: dict[str, Any], dry_run: bool) -> dict[str, Any]:
    if dry_run:
        return {"ok": True, "dry_run": True, "message": "Notify-only dry-run simulated.", "rollback_supported": False}
    result = send_notifications(payload=payload, email_cfg=email_cfg, webhook_cfg=webhook_cfg)
    return {"ok": True, "dry_run": False, "message": "Notifications dispatched.", "result": result, "rollback_supported": False}


def rollback(*_args, **_kwargs) -> dict[str, Any]:
    return {"ok": False, "message": "Rollback is not supported for notify-only actions."}

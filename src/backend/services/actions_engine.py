"""Phase 5 actions engine: creation, transitions, execution, and audit events."""

from __future__ import annotations

from datetime import UTC, datetime
import logging
from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from core.models import ActionEvent, ActionRequest, Setting
from core.database import ensure_settings_schema
from services.executors import EXECUTOR_BY_TYPE
from services.executors_oci import OCI_EXECUTOR_BY_TYPE

TERMINAL_STATES = {"succeeded", "failed", "rolled_back", "rejected"}
logger = logging.getLogger("oci-cost-manager.actions")


def _now() -> datetime:
    return datetime.now(UTC)


def ensure_action_tables(db: Session) -> None:
    try:
        if db.bind is not None and db.bind.dialect.name != "sqlite":
            return
    except Exception:
        pass
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS action_requests (
                action_id VARCHAR(64) PRIMARY KEY,
                source VARCHAR(32) NOT NULL,
                category VARCHAR(32) NOT NULL,
                target_type VARCHAR(32) NOT NULL,
                target_ref JSON NOT NULL,
                proposed_change JSON NOT NULL,
                estimated_savings_monthly FLOAT NOT NULL DEFAULT 0,
                confidence VARCHAR(16) NOT NULL DEFAULT 'low',
                risk_level VARCHAR(16) NOT NULL DEFAULT 'moderate',
                status VARCHAR(32) NOT NULL DEFAULT 'draft',
                requested_by VARCHAR(255),
                approved_by VARCHAR(255),
                created_at DATETIME,
                updated_at DATETIME
            )
            """
        )
    )
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS action_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action_id VARCHAR(64) NOT NULL,
                event_type VARCHAR(32) NOT NULL,
                message TEXT,
                payload JSON,
                timestamp DATETIME
            )
            """
        )
    )
    db.execute(text("CREATE INDEX IF NOT EXISTS idx_actions_status ON action_requests(status)"))
    db.execute(text("CREATE INDEX IF NOT EXISTS idx_actions_category ON action_requests(category)"))
    db.execute(text("CREATE INDEX IF NOT EXISTS idx_actions_created ON action_requests(created_at)"))
    db.execute(text("CREATE INDEX IF NOT EXISTS idx_action_events_action ON action_events(action_id)"))
    db.execute(text("CREATE INDEX IF NOT EXISTS idx_action_events_ts ON action_events(timestamp)"))
    db.commit()


def add_event(db: Session, action_id: str, event_type: str, message: str, payload: dict[str, Any] | None = None) -> None:
    logger.info({"event": "action_event", "action_id": action_id, "event_type": event_type, "message": message})
    db.add(
        ActionEvent(
            action_id=action_id,
            event_type=event_type,
            message=message,
            payload=payload or {},
            timestamp=_now(),
        )
    )


def create_action(
    db: Session,
    *,
    source: str,
    category: str,
    target_type: str,
    target_ref: dict[str, Any],
    proposed_change: dict[str, Any],
    estimated_savings_monthly: float,
    confidence: str,
    risk_level: str,
    requested_by: str,
) -> ActionRequest:
    initial_status = "approved" if risk_level == "safe" else "pending_approval"
    action = ActionRequest(
        source=source,
        category=category,
        target_type=target_type,
        target_ref=target_ref or {},
        proposed_change=proposed_change or {},
        estimated_savings_monthly=float(estimated_savings_monthly or 0.0),
        confidence=confidence,
        risk_level=risk_level,
        status=initial_status,
        requested_by=requested_by,
    )
    db.add(action)
    db.flush()
    add_event(
        db,
        action.action_id,
        "created",
        f"Action created with status {initial_status}.",
        {"risk_level": risk_level, "category": category},
    )
    db.commit()
    db.refresh(action)
    return action


def approve_action(db: Session, action: ActionRequest, approved_by: str, message: str | None = None) -> ActionRequest:
    if action.status in TERMINAL_STATES:
        raise ValueError("Cannot approve an action in terminal state.")
    if action.status in {"approved", "queued", "running"}:
        return action
    action.status = "approved"
    action.approved_by = approved_by
    action.updated_at = _now()
    add_event(db, action.action_id, "approved", message or "Action approved.", {"approved_by": approved_by})
    db.add(action)
    db.commit()
    db.refresh(action)
    return action


def reject_action(db: Session, action: ActionRequest, approved_by: str, message: str | None = None) -> ActionRequest:
    if action.status in TERMINAL_STATES:
        raise ValueError("Cannot reject an action in terminal state.")
    action.status = "rejected"
    action.approved_by = approved_by
    action.updated_at = _now()
    add_event(db, action.action_id, "comment", message or "Action rejected.", {"approved_by": approved_by})
    db.add(action)
    db.commit()
    db.refresh(action)
    return action


def _settings_notification_cfg(db: Session) -> tuple[dict[str, Any], dict[str, Any]]:
    try:
        setting = db.query(Setting).filter(Setting.id == 1).one_or_none()
    except OperationalError:
        ensure_settings_schema()
        try:
            setting = db.query(Setting).filter(Setting.id == 1).one_or_none()
        except Exception:
            setting = None
    email_cfg = {
        "enabled": bool(getattr(setting, "notifications_email_enabled", False)) if setting else False,
        "smtp_host": getattr(setting, "notifications_smtp_host", None) if setting else None,
        "smtp_port": getattr(setting, "notifications_smtp_port", 587) if setting else 587,
        "smtp_username": getattr(setting, "notifications_smtp_username", None) if setting else None,
        "smtp_password": getattr(setting, "notifications_smtp_password", None) if setting else None,
        "email_from": getattr(setting, "notifications_email_from", None) if setting else None,
        "email_to": list(getattr(setting, "notifications_email_to", None) or []) if setting else [],
    }
    webhook_cfg = {
        "enabled": bool(getattr(setting, "notifications_webhook_enabled", False)) if setting else False,
        "url": getattr(setting, "notifications_webhook_url", None) if setting else None,
        "dry_run": bool(getattr(setting, "notifications_webhook_dry_run", True)) if setting else True,
    }
    return email_cfg, webhook_cfg


def run_action(
    db: Session,
    action: ActionRequest,
    *,
    requested_by: str,
    dry_run: bool,
    confirm_delete: bool,
) -> dict[str, Any]:
    if action.status in {"running", "queued", "succeeded"}:
        raise ValueError("Action run is idempotent; this action has already been triggered.")
    if action.status != "approved":
        raise ValueError("Action must be approved before execution.")

    action.status = "queued"
    action.updated_at = _now()
    db.add(action)
    add_event(db, action.action_id, "comment", "Action queued for execution.", {"requested_by": requested_by, "dry_run": dry_run})
    db.commit()

    action.status = "running"
    action.updated_at = _now()
    db.add(action)
    db.commit()

    executor_type = str((action.proposed_change or {}).get("executor_type") or action.category)
    executor = EXECUTOR_BY_TYPE.get(executor_type)
    oci_executor = OCI_EXECUTOR_BY_TYPE.get(executor_type)
    setting = db.query(Setting).filter(Setting.id == 1).one_or_none()
    enable_oci = bool(getattr(setting, "enable_oci_executors", False)) if setting else False
    enable_destructive = bool(getattr(setting, "enable_destructive_actions", False)) if setting else False

    if oci_executor and not enable_oci:
        action.status = "failed"
        add_event(db, action.action_id, "failed", "OCI executors are disabled by feature flag.")
        db.add(action)
        db.commit()
        return {"ok": False, "message": "enable_oci_executors=false"}

    if executor_type in {"cleanup_unattached_volume", "delete_unattached_volume_oci"} and not dry_run and not enable_destructive:
        action.status = "failed"
        add_event(db, action.action_id, "failed", "Destructive actions are disabled by feature flag.")
        db.add(action)
        db.commit()
        return {"ok": False, "message": "enable_destructive_actions=false"}
    if not executor and not oci_executor:
        action.status = "failed"
        add_event(db, action.action_id, "failed", f"No executor found for '{executor_type}'.")
        db.add(action)
        db.commit()
        return {"ok": False, "message": f"No executor for {executor_type}"}

    try:
        if oci_executor:
            if executor_type == "tag_fix_oci":
                result = oci_executor.execute(target_ref=action.target_ref or {}, proposed_change=action.proposed_change or {}, dry_run=dry_run)
            elif executor_type == "stop_instance_oci":
                result = oci_executor.execute(target_ref=action.target_ref or {}, dry_run=dry_run)
            elif executor_type == "delete_unattached_volume_oci":
                result = oci_executor.execute(target_ref=action.target_ref or {}, dry_run=dry_run, confirm_delete=confirm_delete)
            else:
                result = {"ok": False, "message": f"Unsupported OCI executor '{executor_type}'."}
        elif executor_type == "notify_only":
            email_cfg, webhook_cfg = _settings_notification_cfg(db)
            result = executor.execute(
                payload={
                    "action_id": action.action_id,
                    "category": action.category,
                    "target_ref": action.target_ref,
                    "proposed_change": action.proposed_change,
                },
                email_cfg=email_cfg,
                webhook_cfg=webhook_cfg,
                dry_run=dry_run,
            )
        elif executor_type == "cleanup_unattached_volume":
            result = executor.execute(
                target_ref=action.target_ref or {},
                proposed_change=action.proposed_change or {},
                dry_run=dry_run,
                confirm_delete=confirm_delete,
            )
        elif executor_type == "stop_idle_instance":
            result = executor.execute(target_ref=action.target_ref or {}, dry_run=dry_run)
        elif executor_type == "tag_fix":
            result = executor.execute(
                db=db,
                target_ref=action.target_ref or {},
                proposed_change=action.proposed_change or {},
                dry_run=dry_run,
            )
        else:
            result = {"ok": False, "message": f"Unsupported executor '{executor_type}'."}

        if result.get("ok"):
            action.status = "succeeded"
            add_event(db, action.action_id, "executed", result.get("message", "Action executed."), result)
        else:
            action.status = "failed"
            add_event(db, action.action_id, "failed", result.get("message", "Action failed."), result)
    except Exception as exc:
        action.status = "failed"
        add_event(db, action.action_id, "failed", str(exc), {"error": str(exc)})
        result = {"ok": False, "message": str(exc)}

    action.updated_at = _now()
    db.add(action)
    db.commit()
    return result


def rollback_action(db: Session, action: ActionRequest, *, requested_by: str, dry_run: bool) -> dict[str, Any]:
    if action.status != "succeeded":
        raise ValueError("Only succeeded actions can be rolled back.")

    executor_type = str((action.proposed_change or {}).get("executor_type") or action.category)
    executor = EXECUTOR_BY_TYPE.get(executor_type)
    oci_executor = OCI_EXECUTOR_BY_TYPE.get(executor_type)
    if not executor and not oci_executor:
        raise ValueError(f"No executor available for '{executor_type}'.")
    if not oci_executor and not hasattr(executor, "rollback"):
        raise ValueError(f"Rollback not supported for '{executor_type}'.")

    latest_exec_event = (
        db.query(ActionEvent)
        .filter(ActionEvent.action_id == action.action_id, ActionEvent.event_type == "executed")
        .order_by(ActionEvent.timestamp.desc())
        .first()
    )
    payload = (latest_exec_event.payload if latest_exec_event else {}) or {}

    if oci_executor:
        if executor_type == "tag_fix_oci":
            result = oci_executor.rollback(target_ref=action.target_ref or {}, payload=payload, dry_run=dry_run)
        elif executor_type == "stop_instance_oci":
            result = oci_executor.rollback(target_ref=action.target_ref or {}, dry_run=dry_run)
        else:
            result = {"ok": False, "message": f"Rollback not supported for '{executor_type}'."}
    elif executor_type == "tag_fix":
        result = executor.rollback(db=db, target_ref=action.target_ref or {}, payload=payload, dry_run=dry_run)
    elif executor_type == "stop_idle_instance":
        result = executor.rollback(target_ref=action.target_ref or {}, dry_run=dry_run)
    else:
        result = executor.rollback(target_ref=action.target_ref or {}, payload=payload, dry_run=dry_run)

    if result.get("ok"):
        action.status = "rolled_back"
        action.updated_at = _now()
        add_event(db, action.action_id, "rollback", result.get("message", "Rollback completed."), {"requested_by": requested_by, **result})
        db.add(action)
        db.commit()
    else:
        add_event(db, action.action_id, "failed", result.get("message", "Rollback failed."), {"requested_by": requested_by, **result})
        db.commit()
    return result

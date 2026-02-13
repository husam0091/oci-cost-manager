"""Phase 5 action APIs with approval/run/rollback flow."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Optional

from fastapi import APIRouter, Cookie, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from api.schemas.actions import (
    ActionCreateRequestModel,
    ActionCreateResponseModel,
    ActionDecisionRequestModel,
    ActionDetailDataModel,
    ActionDetailResponseModel,
    ActionEventModel,
    ActionListDataModel,
    ActionListResponseModel,
    ActionOperationResponseModel,
    ActionRequestModel,
    ActionRollbackRequestModel,
    ActionRunRequestModel,
)
from core.database import ensure_settings_schema, get_db
from core.models import ActionEvent, ActionRequest, Setting
from core.rbac import can_approve_or_run, can_create_action, has_scope_access, resolve_principal
from services.actions_engine import (
    add_event,
    approve_action,
    create_action,
    ensure_action_tables,
    reject_action,
    rollback_action,
    run_action,
)

router = APIRouter()


def _principal(
    token: Optional[str] = Cookie(default=None, alias="access_token"),
    db: Session = Depends(get_db),
):
    try:
        return resolve_principal(db, token, strict=True)
    except PermissionError as exc:
        raise HTTPException(status_code=401, detail=str(exc))


def _to_action_model(row: ActionRequest) -> ActionRequestModel:
    return ActionRequestModel(
        action_id=row.action_id,
        source=row.source,  # type: ignore[arg-type]
        category=row.category,  # type: ignore[arg-type]
        target_type=row.target_type,  # type: ignore[arg-type]
        target_ref=row.target_ref or {},
        proposed_change=row.proposed_change or {},
        estimated_savings_monthly=float(row.estimated_savings_monthly or 0.0),
        confidence=row.confidence,  # type: ignore[arg-type]
        risk_level=row.risk_level,  # type: ignore[arg-type]
        status=row.status,  # type: ignore[arg-type]
        requested_by=row.requested_by,
        approved_by=row.approved_by,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


@router.post("/actions", response_model=ActionCreateResponseModel)
async def create_action_request(req: ActionCreateRequestModel, db: Session = Depends(get_db), principal=Depends(_principal)):
    ensure_settings_schema()
    ensure_action_tables(db)
    setting = db.query(Setting).filter(Setting.id == 1).one_or_none()
    if bool(getattr(setting, "enable_demo_mode", False)):
        raise HTTPException(status_code=403, detail="Demo mode is read-only for Actions")
    if not can_create_action(principal):
        raise HTTPException(status_code=403, detail="Insufficient permissions to create action")
    if not has_scope_access(
        principal,
        team=(req.target_ref or {}).get("team"),
        app=(req.target_ref or {}).get("app"),
        env=(req.target_ref or {}).get("env"),
        compartment_id=(req.target_ref or {}).get("compartment_id"),
    ):
        raise HTTPException(status_code=403, detail="Out-of-scope action target")
    proposed = dict(req.proposed_change or {})
    if req.recommendation_id:
        proposed.setdefault("recommendation_id", req.recommendation_id)
    if req.budget_alert_id is not None:
        proposed.setdefault("budget_alert_id", req.budget_alert_id)
    if req.notes:
        proposed.setdefault("notes", req.notes)
    action = create_action(
        db,
        source=req.source,
        category=req.category,
        target_type=req.target_type,
        target_ref=req.target_ref or {},
        proposed_change=proposed,
        estimated_savings_monthly=req.estimated_savings_monthly,
        confidence=req.confidence,
        risk_level=req.risk_level,
        requested_by=principal.username or "unknown",
    )
    return ActionCreateResponseModel(success=True, data=_to_action_model(action))


@router.get("/actions", response_model=ActionListResponseModel)
async def list_actions(
    status: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    team: Optional[str] = Query(None),
    app: Optional[str] = Query(None),
    env: Optional[str] = Query(None),
    compartment_id: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    principal=Depends(_principal),
):
    ensure_action_tables(db)
    rows = db.query(ActionRequest).order_by(ActionRequest.created_at.desc()).all()
    out: list[ActionRequest] = []
    for row in rows:
        target = row.target_ref or {}
        created = row.created_at.replace(tzinfo=UTC) if row.created_at and row.created_at.tzinfo is None else row.created_at
        if status and row.status != status:
            continue
        if category and row.category != category:
            continue
        if team and target.get("team") != team:
            continue
        if app and target.get("app") != app:
            continue
        if env and target.get("env") != env:
            continue
        if compartment_id and target.get("compartment_id") != compartment_id:
            continue
        if start_date and created and created < datetime.fromisoformat(start_date).replace(tzinfo=UTC):
            continue
        if end_date and created and created > datetime.fromisoformat(end_date).replace(tzinfo=UTC):
            continue
        if not has_scope_access(
            principal,
            team=target.get("team"),
            app=target.get("app"),
            env=target.get("env"),
            compartment_id=target.get("compartment_id"),
        ):
            continue
        out.append(row)
    return ActionListResponseModel(success=True, data=ActionListDataModel(items=[_to_action_model(r) for r in out]))


@router.get("/actions/{action_id}", response_model=ActionDetailResponseModel)
async def get_action(action_id: str, db: Session = Depends(get_db), principal=Depends(_principal)):
    ensure_action_tables(db)
    action = db.query(ActionRequest).filter(ActionRequest.action_id == action_id).one_or_none()
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")
    target = action.target_ref or {}
    if not has_scope_access(
        principal,
        team=target.get("team"),
        app=target.get("app"),
        env=target.get("env"),
        compartment_id=target.get("compartment_id"),
    ):
        raise HTTPException(status_code=404, detail="Action not found")
    events = (
        db.query(ActionEvent)
        .filter(ActionEvent.action_id == action_id)
        .order_by(ActionEvent.timestamp.asc(), ActionEvent.id.asc())
        .all()
    )
    return ActionDetailResponseModel(
        success=True,
        data=ActionDetailDataModel(
            action=_to_action_model(action),
            timeline=[
                ActionEventModel(
                    event_type=e.event_type,  # type: ignore[arg-type]
                    message=e.message,
                    payload=e.payload or {},
                    timestamp=e.timestamp,
                )
                for e in events
            ],
        ),
    )


@router.post("/actions/{action_id}/approve", response_model=ActionOperationResponseModel)
async def approve(action_id: str, req: ActionDecisionRequestModel, db: Session = Depends(get_db), principal=Depends(_principal)):
    ensure_settings_schema()
    ensure_action_tables(db)
    setting = db.query(Setting).filter(Setting.id == 1).one_or_none()
    if bool(getattr(setting, "enable_demo_mode", False)):
        raise HTTPException(status_code=403, detail="Demo mode is read-only for Actions")
    action = db.query(ActionRequest).filter(ActionRequest.action_id == action_id).one_or_none()
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")
    if not can_approve_or_run(principal, action.risk_level):
        raise HTTPException(status_code=403, detail="Insufficient permissions to approve this action")
    try:
        updated = approve_action(db, action, approved_by=principal.username or "admin", message=req.message)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return ActionOperationResponseModel(success=True, data={"action_id": updated.action_id, "status": updated.status})


@router.post("/actions/{action_id}/reject", response_model=ActionOperationResponseModel)
async def reject(action_id: str, req: ActionDecisionRequestModel, db: Session = Depends(get_db), principal=Depends(_principal)):
    ensure_settings_schema()
    ensure_action_tables(db)
    setting = db.query(Setting).filter(Setting.id == 1).one_or_none()
    if bool(getattr(setting, "enable_demo_mode", False)):
        raise HTTPException(status_code=403, detail="Demo mode is read-only for Actions")
    action = db.query(ActionRequest).filter(ActionRequest.action_id == action_id).one_or_none()
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")
    if not can_approve_or_run(principal, action.risk_level):
        raise HTTPException(status_code=403, detail="Insufficient permissions to reject this action")
    try:
        updated = reject_action(db, action, approved_by=principal.username or "admin", message=req.message)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return ActionOperationResponseModel(success=True, data={"action_id": updated.action_id, "status": updated.status})


@router.post("/actions/{action_id}/run", response_model=ActionOperationResponseModel)
async def run(action_id: str, req: ActionRunRequestModel, db: Session = Depends(get_db), principal=Depends(_principal)):
    ensure_action_tables(db)
    ensure_settings_schema()
    action = db.query(ActionRequest).filter(ActionRequest.action_id == action_id).one_or_none()
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")
    if not can_approve_or_run(principal, action.risk_level):
        raise HTTPException(status_code=403, detail="Insufficient permissions to run this action")
    try:
        setting = db.query(Setting).filter(Setting.id == 1).one_or_none()
    except Exception:
        setting = None
    if bool(getattr(setting, "enable_demo_mode", False)):
        raise HTTPException(status_code=403, detail="Demo mode is read-only for Actions")
    executor_type = str((action.proposed_change or {}).get("executor_type") or action.category)
    if executor_type in {"tag_fix_oci", "stop_instance_oci", "delete_unattached_volume_oci"} and not bool(getattr(setting, "enable_oci_executors", False)):
        raise HTTPException(status_code=403, detail="enable_oci_executors=false")
    if executor_type in {"cleanup_unattached_volume", "delete_unattached_volume_oci"} and not req.dry_run and not bool(getattr(setting, "enable_destructive_actions", False)):
        raise HTTPException(status_code=403, detail="enable_destructive_actions=false")
    try:
        result = run_action(
            db,
            action,
            requested_by=principal.username or "admin",
            dry_run=bool(req.dry_run),
            confirm_delete=bool(req.confirm_delete),
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    updated = db.query(ActionRequest).filter(ActionRequest.action_id == action_id).one()
    return ActionOperationResponseModel(success=True, data={"action_id": updated.action_id, "status": updated.status, "result": result})


@router.post("/actions/{action_id}/rollback", response_model=ActionOperationResponseModel)
async def rollback(action_id: str, req: ActionRollbackRequestModel, db: Session = Depends(get_db), principal=Depends(_principal)):
    ensure_settings_schema()
    ensure_action_tables(db)
    setting = db.query(Setting).filter(Setting.id == 1).one_or_none()
    if bool(getattr(setting, "enable_demo_mode", False)):
        raise HTTPException(status_code=403, detail="Demo mode is read-only for Actions")
    action = db.query(ActionRequest).filter(ActionRequest.action_id == action_id).one_or_none()
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")
    if not can_approve_or_run(principal, action.risk_level):
        raise HTTPException(status_code=403, detail="Insufficient permissions to rollback this action")
    try:
        result = rollback_action(db, action, requested_by=principal.username or "admin", dry_run=bool(req.dry_run))
        if req.message:
            add_event(db, action.action_id, "comment", req.message, {"requested_by": principal.username or "admin"})
            db.commit()
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    updated = db.query(ActionRequest).filter(ActionRequest.action_id == action_id).one()
    return ActionOperationResponseModel(success=True, data={"action_id": updated.action_id, "status": updated.status, "result": result})

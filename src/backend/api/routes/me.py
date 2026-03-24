"""Current user principal endpoint."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Cookie, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from core.config import get_settings as get_app_settings
from core.database import ensure_settings_schema, get_db
from core.models import Budget, ScanRun, Setting, UserAccount
from core.rbac import feature_flags, resolve_principal, role_job_profile

router = APIRouter()


@router.get("/me")
async def me(
    token: Optional[str] = Cookie(default=None, alias="access_token"),
    db: Session = Depends(get_db),
):
    ensure_settings_schema()
    # If users exist in the DB, require a valid JWT so the login page is shown
    has_users = db.query(UserAccount).filter(UserAccount.is_active == True).count() > 0
    strict = has_users
    try:
        principal = resolve_principal(db, token, strict=strict)
    except PermissionError as exc:
        raise HTTPException(status_code=401, detail=str(exc))
    setting = db.query(Setting).filter(Setting.id == 1).one_or_none()
    scan_count = int(db.query(func.count(ScanRun.id)).scalar() or 0)
    budget_count = int(db.query(func.count(Budget.budget_id)).scalar() or 0)
    important = list(getattr(setting, "important_compartments", None) or getattr(setting, "important_compartment_ids", None) or []) if setting else []
    flags = feature_flags(setting)
    app_settings = get_app_settings()
    return {
        "success": True,
        "data": {
            "username": principal.username,
            "role": principal.role,
            "role_profile": role_job_profile(principal.role),
            "allowed_teams": principal.allowed_teams,
            "allowed_apps": principal.allowed_apps,
            "allowed_envs": principal.allowed_envs,
            "allowed_compartment_ids": principal.allowed_compartment_ids,
            "feature_flags": flags,
            "app_version": app_settings.app_version,
            "product_state": {
                "has_scans": scan_count > 0,
                "has_budgets": budget_count > 0,
                "has_important_compartments": len(important) > 0,
                "has_recommendations": scan_count > 0,
                "is_empty_system": scan_count == 0 and budget_count == 0,
            },
        },
    }

"""Ops metrics endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from core.cache import get_cache_info, get_cache_metrics
from core.config import get_settings as get_app_settings
from core.database import ensure_settings_schema, get_db
from core.models import ActionRequest, BudgetAlertEvent, BudgetDailySnapshot, ScanRun, Setting
from core.rbac import feature_flags

router = APIRouter()


@router.get("/ops/metrics")
async def ops_metrics(db: Session = Depends(get_db)):
    ensure_settings_schema()
    app_settings = get_app_settings()
    scan_count = db.query(func.count(ScanRun.id)).scalar() or 0
    action_count = db.query(func.count(ActionRequest.action_id)).scalar() or 0
    alert_count = db.query(func.count(BudgetAlertEvent.id)).scalar() or 0
    breach_count = db.query(func.count(BudgetDailySnapshot.id)).filter(BudgetDailySnapshot.utilization_pct >= 100).scalar() or 0
    cache_metrics = get_cache_metrics()
    setting = db.query(Setting).filter(Setting.id == 1).one_or_none()
    return {
        "success": True,
        "data": {
            "app_version": app_settings.app_version,
            "scans": int(scan_count),
            "actions": int(action_count),
            "alerts": int(alert_count),
            "budget_breaches": int(breach_count),
            "cache_hit_ratio": cache_metrics.get("hit_ratio", 0.0),
            "cache": get_cache_info(),
            "feature_flags": feature_flags(setting),
        },
    }

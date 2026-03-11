"""Budget CRUD, status, and legacy budget validation endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Cookie, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.schemas.budgets import (
    BudgetCreateUpdateModel,
    BudgetDeleteResponseModel,
    BudgetHistoryItemModel,
    BudgetHistoryResponseModel,
    BudgetListResponseModel,
    BudgetModel,
    BudgetMutationResponseModel,
    BudgetStatusItemModel,
    BudgetStatusResponseModel,
)
from core.cache import clear_cache, get_cached, set_cached
from core.database import get_db
from core.models import Budget, BudgetDailySnapshot
from core.rbac import resolve_principal
from services import evaluate_budget_statuses, get_budget_validator
from services.budget_engine import ensure_budget_tables

router = APIRouter()
BUDGET_STATUS_CACHE_TTL = 90


def _to_budget_model(row: Budget) -> BudgetModel:
    return BudgetModel(
        budget_id=row.budget_id,
        name=row.name,
        scope_type=row.scope_type,  # type: ignore[arg-type]
        scope_value=row.scope_value,
        include_children=bool(row.include_children),
        period=row.period,  # type: ignore[arg-type]
        limit_amount=float(row.limit_amount),
        currency=row.currency,
        growth_cap_pct=float(row.growth_cap_pct) if row.growth_cap_pct is not None else None,
        forecast_guardrail_pct=float(row.forecast_guardrail_pct) if row.forecast_guardrail_pct is not None else None,
        alert_thresholds=[int(x) for x in (row.alert_thresholds or [50, 75, 90, 100])],
        compare_mode=row.compare_mode,  # type: ignore[arg-type]
        enabled=bool(row.enabled),
        notifications_enabled=bool(getattr(row, "notifications_enabled", False)),
        owner=row.owner,
        start_date=row.start_date,
        end_date=row.end_date,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


@router.get("", response_model=BudgetListResponseModel)
async def list_budgets(
    token: Optional[str] = Cookie(default=None, alias="access_token"),
    db: Session = Depends(get_db),
):
    ensure_budget_tables(db)
    principal = resolve_principal(db, token, strict=False)
    rows = db.query(Budget).order_by(Budget.created_at.asc()).all()
    if principal.is_admin:
        return BudgetListResponseModel(success=True, data=[_to_budget_model(r) for r in rows])
    filtered = []
    for row in rows:
        if row.scope_type == "team" and principal.allowed_teams and row.scope_value not in principal.allowed_teams:
            continue
        if row.scope_type == "app" and principal.allowed_apps and row.scope_value not in principal.allowed_apps:
            continue
        if row.scope_type == "env" and principal.allowed_envs and row.scope_value not in principal.allowed_envs:
            continue
        if row.scope_type == "compartment" and principal.allowed_compartment_ids and row.scope_value not in principal.allowed_compartment_ids:
            continue
        filtered.append(row)
    return BudgetListResponseModel(success=True, data=[_to_budget_model(r) for r in filtered])


@router.post("", response_model=BudgetMutationResponseModel)
async def create_budget(
    req: BudgetCreateUpdateModel,
    token: Optional[str] = Cookie(default=None, alias="access_token"),
    db: Session = Depends(get_db),
):
    ensure_budget_tables(db)
    principal = resolve_principal(db, token, strict=False)
    if not principal.is_admin:
        raise HTTPException(status_code=403, detail="Admin role required")
    row = Budget(
        name=req.name,
        scope_type=req.scope_type,
        scope_value=req.scope_value,
        include_children=bool(req.include_children),
        period=req.period,
        limit_amount=float(req.limit_amount),
        currency=req.currency,
        growth_cap_pct=req.growth_cap_pct,
        forecast_guardrail_pct=req.forecast_guardrail_pct,
        alert_thresholds=req.alert_thresholds,
        compare_mode=req.compare_mode,
        enabled=bool(req.enabled),
        notifications_enabled=bool(req.notifications_enabled),
        owner=req.owner,
        start_date=req.start_date,
        end_date=req.end_date,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    clear_cache()
    return BudgetMutationResponseModel(success=True, data=_to_budget_model(row))


@router.put("/{budget_id}", response_model=BudgetMutationResponseModel)
async def update_budget(
    budget_id: str,
    req: BudgetCreateUpdateModel,
    token: Optional[str] = Cookie(default=None, alias="access_token"),
    db: Session = Depends(get_db),
):
    ensure_budget_tables(db)
    principal = resolve_principal(db, token, strict=False)
    if not principal.is_admin:
        raise HTTPException(status_code=403, detail="Admin role required")
    row = db.query(Budget).filter(Budget.budget_id == budget_id).one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Budget not found")
    row.name = req.name
    row.scope_type = req.scope_type
    row.scope_value = req.scope_value
    row.include_children = bool(req.include_children)
    row.period = req.period
    row.limit_amount = float(req.limit_amount)
    row.currency = req.currency
    row.growth_cap_pct = req.growth_cap_pct
    row.forecast_guardrail_pct = req.forecast_guardrail_pct
    row.alert_thresholds = req.alert_thresholds
    row.compare_mode = req.compare_mode
    row.enabled = bool(req.enabled)
    row.notifications_enabled = bool(req.notifications_enabled)
    row.owner = req.owner
    row.start_date = req.start_date
    row.end_date = req.end_date
    row.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    clear_cache()
    return BudgetMutationResponseModel(success=True, data=_to_budget_model(row))


@router.delete("/{budget_id}", response_model=BudgetDeleteResponseModel)
async def delete_budget(
    budget_id: str,
    token: Optional[str] = Cookie(default=None, alias="access_token"),
    db: Session = Depends(get_db),
):
    ensure_budget_tables(db)
    principal = resolve_principal(db, token, strict=False)
    if not principal.is_admin:
        raise HTTPException(status_code=403, detail="Admin role required")
    row = db.query(Budget).filter(Budget.budget_id == budget_id).one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Budget not found")
    db.delete(row)
    db.commit()
    clear_cache()
    return BudgetDeleteResponseModel(success=True)


@router.get("/status", response_model=BudgetStatusResponseModel)
async def budget_status(
    token: Optional[str] = Cookie(default=None, alias="access_token"),
    db: Session = Depends(get_db),
):
    ensure_budget_tables(db)
    principal = resolve_principal(db, token, strict=False)
    cache_key = "budgets_status_v1"
    cached = get_cached(cache_key)
    if cached is not None:
        return BudgetStatusResponseModel(**cached)

    statuses = evaluate_budget_statuses(db, persist_alerts=True)
    filtered_statuses = []
    for s in statuses:
        if principal.is_admin:
            filtered_statuses.append(s)
            continue
        if s.scope_type == "team" and principal.allowed_teams and s.scope_value not in principal.allowed_teams:
            continue
        if s.scope_type == "app" and principal.allowed_apps and s.scope_value not in principal.allowed_apps:
            continue
        if s.scope_type == "env" and principal.allowed_envs and s.scope_value not in principal.allowed_envs:
            continue
        if s.scope_type == "compartment" and principal.allowed_compartment_ids and s.scope_value not in principal.allowed_compartment_ids:
            continue
        filtered_statuses.append(s)

    out = BudgetStatusResponseModel(
        success=True,
        data=[
            BudgetStatusItemModel(
                budget_id=s.budget_id,
                budget_name=s.budget_name,
                scope_type=s.scope_type,  # type: ignore[arg-type]
                scope_value=s.scope_value,
                current_spend=round(s.current_spend, 2),
                budget_limit=round(s.budget_limit, 2),
                utilization_pct=round(s.utilization_pct, 2),
                forecast_end_of_month=round(s.forecast_end_of_month, 2),
                breach_level=s.breach_level,  # type: ignore[arg-type]
                days_remaining=s.days_remaining,
                explanation=s.explanation,
                narrative=getattr(s, "narrative", ""),
                latest_threshold_crossed=s.latest_threshold_crossed,
            )
            for s in filtered_statuses
        ],
    )
    set_cached(cache_key, out.model_dump(), BUDGET_STATUS_CACHE_TTL)
    return out


@router.get("/history", response_model=BudgetHistoryResponseModel)
async def budget_history(
    budget_id: str = Query(...),
    token: Optional[str] = Cookie(default=None, alias="access_token"),
    db: Session = Depends(get_db),
):
    ensure_budget_tables(db)
    principal = resolve_principal(db, token, strict=False)
    budget = db.query(Budget).filter(Budget.budget_id == budget_id).one_or_none()
    if not budget:
        return BudgetHistoryResponseModel(success=True, data=[])
    if not principal.is_admin:
        if budget.scope_type == "team" and principal.allowed_teams and budget.scope_value not in principal.allowed_teams:
            raise HTTPException(status_code=404, detail="Budget not found")
        if budget.scope_type == "app" and principal.allowed_apps and budget.scope_value not in principal.allowed_apps:
            raise HTTPException(status_code=404, detail="Budget not found")
        if budget.scope_type == "env" and principal.allowed_envs and budget.scope_value not in principal.allowed_envs:
            raise HTTPException(status_code=404, detail="Budget not found")
        if budget.scope_type == "compartment" and principal.allowed_compartment_ids and budget.scope_value not in principal.allowed_compartment_ids:
            raise HTTPException(status_code=404, detail="Budget not found")
    rows = (
        db.query(BudgetDailySnapshot)
        .filter(BudgetDailySnapshot.budget_id == budget_id)
        .order_by(BudgetDailySnapshot.snapshot_date.asc())
        .all()
    )
    return BudgetHistoryResponseModel(
        success=True,
        data=[
            BudgetHistoryItemModel(
                snapshot_date=r.snapshot_date,
                current_spend=round(float(r.current_spend or 0.0), 2),
                utilization_pct=round(float(r.utilization_pct or 0.0), 2),
                forecast_end_of_month=round(float(r.forecast_end_of_month or 0.0), 2),
            )
            for r in rows
        ],
    )


# Legacy endpoints retained for backward compatibility.
class BudgetValidateRequest(BaseModel):
    budget_amount: float
    period_type: str = "monthly"  # monthly or yearly
    compartment_id: Optional[str] = None
    warning_threshold: int = 80


@router.post("/validate")
async def validate_budget(request: BudgetValidateRequest):
    try:
        validator = get_budget_validator()
        result = validator.validate_budget(
            budget_amount=request.budget_amount,
            period_type=request.period_type,
            compartment_id=request.compartment_id,
            warning_threshold=request.warning_threshold,
        )
        recommendations = validator.get_budget_recommendations(result)
        return {"success": True, "data": {**result, "recommendations": recommendations}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/check")
async def quick_budget_check(
    budget: float = Query(..., description="Budget amount"),
    period: str = Query("monthly", description="Period: monthly or yearly"),
):
    try:
        validator = get_budget_validator()
        result = validator.validate_budget(budget_amount=budget, period_type=period)
        return {
            "success": True,
            "data": {
                "budget": budget,
                "actual": result["actual_amount"],
                "status": result["status"],
                "consumption_pct": result["consumption_pct"],
                "variance": result["variance"],
                "projected_total": result["projected_total"],
                "projected_status": result["projected_status"],
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/forecast")
async def get_budget_forecast(
    budget: float = Query(..., description="Budget amount"),
    period: str = Query("monthly", description="Period: monthly or yearly"),
):
    try:
        validator = get_budget_validator()
        result = validator.validate_budget(budget_amount=budget, period_type=period)
        daily_burn = result["daily_burn_rate"]
        days_remaining = result["days_remaining"]
        remaining_budget = budget - result["actual_amount"]
        days_to_exhaustion = (remaining_budget / daily_burn) if daily_burn > 0 else float("inf")
        safe_daily_spend = (remaining_budget / days_remaining) if days_remaining > 0 else 0
        return {
            "success": True,
            "data": {
                "budget": budget,
                "actual": result["actual_amount"],
                "remaining": remaining_budget,
                "daily_burn_rate": daily_burn,
                "projected_total": result["projected_total"],
                "projected_variance": result["projected_variance"],
                "days_to_exhaustion": round(days_to_exhaustion, 1) if days_to_exhaustion != float("inf") else None,
                "safe_daily_spend": round(safe_daily_spend, 2),
                "status": result["status"],
                "projected_status": result["projected_status"],
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

"""Governance APIs: allocation rules and tag coverage."""

from __future__ import annotations

from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, Cookie, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from api.utils.dates import compute_previous_period, iso_date, parse_required_range
from core.auth import decode_token
from core.cache import clear_cache, get_cached, set_cached
from core.database import get_db
from core.models import AllocationRule, Resource
from services import get_cost_calculator
from services.allocation import ensure_allocation_rules_table, evaluate_allocation, load_enabled_rules

router = APIRouter()
GOV_CACHE_TTL = 90


class AllocationRulePayload(BaseModel):
    name: str
    is_enabled: bool = True
    match_type: str
    match_expression: str
    set_env: Optional[str] = None
    set_team: Optional[str] = None
    set_app: Optional[str] = None
    priority: int = Field(default=100, ge=0, le=100000)


def _require_admin(token: Optional[str] = Cookie(default=None, alias="access_token")):
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    data = decode_token(token)
    if not data or not data.get("sub"):
        raise HTTPException(status_code=401, detail="Invalid token")
    return data


@router.get("/governance/tag-coverage")
async def get_tag_coverage(
    start_date: str = Query(...),
    end_date: str = Query(...),
    db: Session = Depends(get_db),
):
    cache_key = f"governance_tag_coverage|start={start_date}|end={end_date}"
    cached = get_cached(cache_key)
    if cached is not None:
        return cached

    start, end_exclusive, days = parse_required_range(start_date, end_date)
    prev_start, prev_end = compute_previous_period(start, end_exclusive)
    calc = get_cost_calculator()

    current_rows = calc.get_costs_by_resource(start, end_exclusive, include_skus=True)
    previous_rows = calc.get_costs_by_resource(prev_start, prev_end, include_skus=True)
    all_ids = list({
        *(r.get("resource_id") for r in current_rows if r.get("resource_id")),
        *(r.get("resource_id") for r in previous_rows if r.get("resource_id")),
    })
    resources = db.query(Resource).filter(Resource.ocid.in_(all_ids)).all() if all_ids else []
    resource_map = {r.ocid: r for r in resources}
    rules = load_enabled_rules(db)

    def _analyze(rows: list[dict]) -> dict:
        total_cost = 0.0
        env_ok = team_ok = app_ok = 0
        count = 0
        unowned_cost = 0.0
        missing_compartments: dict[str, float] = {}
        missing_services: dict[str, float] = {}
        for row in rows:
            rid = row.get("resource_id")
            resource = resource_map.get(rid)
            cost = float(row.get("total_cost") or 0.0)
            skus = row.get("skus") or []
            sku_text = " ".join((s.get("sku_name") or "") for s in skus)
            alloc = evaluate_allocation(resource, rules, compartment_name=row.get("compartment_name"), sku_text=sku_text)
            total_cost += cost
            count += 1
            if alloc.env != "Unallocated":
                env_ok += 1
            if alloc.team != "Unallocated":
                team_ok += 1
            if alloc.app != "Unallocated":
                app_ok += 1
            if alloc.env == "Unallocated" or alloc.team == "Unallocated" or alloc.app == "Unallocated":
                unowned_cost += cost
                comp = row.get("compartment_name") or row.get("compartment_id") or "Unknown"
                missing_compartments[comp] = missing_compartments.get(comp, 0.0) + cost
                service = "Compute"
                low_sku = sku_text.lower()
                if "storage" in low_sku or "backup" in low_sku or "volume" in low_sku or "snapshot" in low_sku:
                    service = "Storage"
                elif "sql" in low_sku or "database" in low_sku:
                    service = "Database"
                elif "network" in low_sku:
                    service = "Network"
                missing_services[service] = missing_services.get(service, 0.0) + cost
        return {
            "total_cost": round(total_cost, 2),
            "coverage": {
                "env_pct": round((env_ok / max(count, 1)) * 100.0, 2),
                "team_pct": round((team_ok / max(count, 1)) * 100.0, 2),
                "app_pct": round((app_ok / max(count, 1)) * 100.0, 2),
            },
            "unowned_cost": round(unowned_cost, 2),
            "missing_compartments": missing_compartments,
            "missing_services": missing_services,
        }

    current = _analyze(current_rows)
    previous = _analyze(previous_rows)
    delta_unowned = current["unowned_cost"] - previous["unowned_cost"]

    response = {
        "success": True,
        "data": {
            "period": {
                "start_date": iso_date(start),
                "end_date": iso_date(end_exclusive - timedelta(days=1)),
                "days": days,
            },
            "totals": {
                "current": current["total_cost"],
                "previous": previous["total_cost"],
            },
            "coverage": current["coverage"],
            "unowned_cost": {
                "current": current["unowned_cost"],
                "previous": previous["unowned_cost"],
                "delta_abs": round(delta_unowned, 2),
                "delta_pct": round((delta_unowned / previous["unowned_cost"] * 100.0) if previous["unowned_cost"] else 0.0, 2),
            },
            "top_missing_compartments": [
                {"name": name, "cost": round(cost, 2)}
                for name, cost in sorted(current["missing_compartments"].items(), key=lambda kv: kv[1], reverse=True)[:8]
            ],
            "top_missing_services": [
                {"name": name, "cost": round(cost, 2)}
                for name, cost in sorted(current["missing_services"].items(), key=lambda kv: kv[1], reverse=True)[:8]
            ],
        },
    }
    set_cached(cache_key, response, GOV_CACHE_TTL)
    return response


@router.get("/admin/allocation-rules")
async def list_allocation_rules(db: Session = Depends(get_db), user=Depends(_require_admin)):
    ensure_allocation_rules_table(db)
    rows = db.query(AllocationRule).order_by(AllocationRule.priority.asc(), AllocationRule.id.asc()).all()
    return {
        "success": True,
        "data": [
            {
                "id": r.id,
                "name": r.name,
                "is_enabled": r.is_enabled,
                "match_type": r.match_type,
                "match_expression": r.match_expression,
                "set_env": r.set_env,
                "set_team": r.set_team,
                "set_app": r.set_app,
                "priority": r.priority,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "updated_at": r.updated_at.isoformat() if r.updated_at else None,
            }
            for r in rows
        ],
    }


@router.post("/admin/allocation-rules")
async def create_allocation_rule(req: AllocationRulePayload, db: Session = Depends(get_db), user=Depends(_require_admin)):
    ensure_allocation_rules_table(db)
    row = AllocationRule(**req.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    clear_cache()
    return {"success": True, "data": {"id": row.id}}


@router.put("/admin/allocation-rules/{rule_id}")
async def update_allocation_rule(rule_id: int, req: AllocationRulePayload, db: Session = Depends(get_db), user=Depends(_require_admin)):
    ensure_allocation_rules_table(db)
    row = db.query(AllocationRule).filter(AllocationRule.id == rule_id).one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Rule not found")
    for key, value in req.model_dump().items():
        setattr(row, key, value)
    db.commit()
    clear_cache()
    return {"success": True}


@router.delete("/admin/allocation-rules/{rule_id}")
async def delete_allocation_rule(rule_id: int, db: Session = Depends(get_db), user=Depends(_require_admin)):
    ensure_allocation_rules_table(db)
    row = db.query(AllocationRule).filter(AllocationRule.id == rule_id).one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Rule not found")
    db.delete(row)
    db.commit()
    clear_cache()
    return {"success": True}

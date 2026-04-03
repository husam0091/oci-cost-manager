"""Data routes that serve from the database only."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from core.database import get_db
from core.models import AllocationRule, Resource, Compartment, CostSnapshot, TrendPoint
from services.allocation import evaluate_allocation, load_enabled_rules

router = APIRouter()


@router.get("/resources")
async def data_resources(
    compartment_id: Optional[str] = Query(None),
    type: Optional[str] = Query(None, description="resource type filter"),
    env: Optional[str] = Query(None),
    team: Optional[str] = Query(None),
    app: Optional[str] = Query(None),
    unowned_only: bool = Query(False),
    search: Optional[str] = Query(None, description="search by name or IP (case-insensitive, partial match)"),
    region: Optional[str] = Query(None, description="filter by OCI region"),
    limit: int = Query(500, ge=1, le=5000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    q = db.query(Resource)
    if compartment_id:
        q = q.filter(Resource.compartment_id == compartment_id)
    if region and region != "all":
        q = q.filter(Resource.region == region)
    if type:
        q = q.filter(Resource.type == type)
    if search:
        from sqlalchemy import func, cast
        from sqlalchemy import String
        term = f"%{search.strip()}%"
        q = q.filter(
            Resource.name.ilike(term) |
            cast(Resource.details["private_ip"], String).ilike(term)
        )
    total = q.count()
    rows = q.order_by(Resource.name.asc()).offset(offset).limit(limit).all()
    rules = load_enabled_rules(db)
    data = [{
        "id": r.ocid, "name": r.name, "type": r.type, "compartment_id": r.compartment_id,
        "region": r.region, "status": r.status, "shape": r.shape, "details": r.details
    } for r in rows]
    enriched = []
    for item, model in zip(data, rows):
        alloc = evaluate_allocation(model, rules, compartment_name=None, sku_text="")
        details = model.details or {}
        item["env"] = details.get("env") or alloc.env
        item["team"] = details.get("team") or alloc.team
        item["app"] = details.get("app") or alloc.app
        item["allocation_confidence"] = details.get("allocation_confidence") or alloc.allocation_confidence
        item["allocation_reason"] = details.get("allocation_reason") or alloc.allocation_reason
        if env and item["env"] != env:
            continue
        if team and item["team"] != team:
            continue
        if app and item["app"] != app:
            continue
        if unowned_only and not (item["env"] == "Unallocated" or item["team"] == "Unallocated" or item["app"] == "Unallocated"):
            continue
        enriched.append(item)
    data = enriched
    return {"success": True, "data": data, "meta": {"total": total, "returned": len(data), "offset": offset}}


@router.get("/compartments/tree")
async def data_compartments_tree(db: Session = Depends(get_db)):
    rows = db.query(Compartment).all()
    if not rows:
        return {"success": True, "data": None}
    nodes = {c.id: {"id": c.id, "name": c.name, "parent_id": c.parent_id, "children": []} for c in rows}
    root = None
    for c in rows:
        if not c.parent_id or c.id == c.parent_id:
            root = nodes[c.id]
        else:
            parent = nodes.get(c.parent_id)
            if parent:
                parent["children"].append(nodes[c.id])
    return {"success": True, "data": root or list(nodes.values())[0]}


@router.get("/costs")
async def data_costs(period: str = Query("monthly"), db: Session = Depends(get_db)):
    row = db.query(CostSnapshot).filter(CostSnapshot.period == period).order_by(CostSnapshot.start_date.desc()).first()
    if not row:
        return {"success": True, "data": None}
    return {"success": True, "data": {
        "period": row.period,
        "start_date": row.start_date.isoformat(),
        "end_date": row.end_date.isoformat() if row.end_date else None,
        "total": row.total,
        "by_service": row.by_service or {},
    }}


@router.get("/trends")
async def data_trends(months: int = Query(6, ge=1, le=24), db: Session = Depends(get_db)):
    rows = db.query(TrendPoint).order_by(TrendPoint.month_start.desc()).limit(months).all()
    out = [{
        "month": r.month, "month_name": r.month, "total_cost": r.total_cost, "by_service": r.by_service or {}
    } for r in reversed(rows)]
    return {"success": True, "data": out}

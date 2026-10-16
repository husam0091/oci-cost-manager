"""Data routes that serve from the database only."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Literal, Optional

from core.database import get_db
from core.models import Resource, Compartment, CostSnapshot, TrendPoint
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
    status: Optional[str] = Query(None, description="Lifecycle state filter"),
    sort_by: Literal["name", "type", "region", "status", "updated_at"] = Query("name"),
    sort_order: Literal["asc", "desc"] = Query("asc"),
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
    if status:
        q = q.filter(Resource.status == status)
    if search and search.strip():
        from sqlalchemy import cast
        from sqlalchemy import String
        # Treat wildcard characters as literal search input.
        term = "%" + search.strip().replace("/", "//").replace("%", "/%").replace("_", "/_") + "%"
        q = q.filter(
            Resource.name.ilike(term, escape="/") |
            cast(Resource.details["private_ip"], String).ilike(term, escape="/")
        )
    # A unique tie-breaker keeps pages deterministic when names are duplicated.
    column = getattr(Resource, sort_by)
    q = q.order_by(column.desc() if sort_order == "desc" else column.asc(), Resource.ocid.asc())
    rules = load_enabled_rules(db)
    allocation_filters = bool(env or team or app or unowned_only)

    def enrich(model):
        alloc = evaluate_allocation(model, rules, compartment_name=None, sku_text="")
        details = model.details or {}
        return {
            "id": model.ocid, "name": model.name, "type": model.type,
            "compartment_id": model.compartment_id, "region": model.region,
            "status": model.status, "shape": model.shape, "details": model.details,
            "env": details.get("env") or alloc.env,
            "team": details.get("team") or alloc.team,
            "app": details.get("app") or alloc.app,
            "allocation_confidence": details.get("allocation_confidence") or alloc.allocation_confidence,
            "allocation_reason": details.get("allocation_reason") or alloc.allocation_reason,
        }

    if not allocation_filters:
        total = q.count()
        data = [enrich(row) for row in q.offset(offset).limit(limit).all()]
    else:
        # Rule-derived ownership cannot be filtered in SQL. Stream the candidates,
        # count all matches, and keep only this page in memory. Filtering must
        # precede slicing or matches beyond the first SQL page are lost.
        data = []
        total = 0
        for row in q.yield_per(500):
            item = enrich(row)
            if any(value and item[key] != value for key, value in (("env", env), ("team", team), ("app", app))):
                continue
            if unowned_only and not any(item[key] == "Unallocated" for key in ("env", "team", "app")):
                continue
            if offset <= total < offset + limit:
                data.append(item)
            total += 1
    return {"success": True, "data": data, "meta": {
        "total": total, "returned": len(data), "offset": offset,
        "limit": limit, "has_more": offset + len(data) < total,
        "sort_by": sort_by, "sort_order": sort_order,
    }}


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

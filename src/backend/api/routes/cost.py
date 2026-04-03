"""Phase 3 fast cost endpoints (cache -> snapshot -> aggregates)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session

from core.database import get_db
from core.models import CostByCompartment, CostByResource, CostSnapshot, DailyCostByService
from core.redis_cache import cache_get, cache_set
from services.aggregate_engine import latest_snapshot, resolve_range

router = APIRouter()

SUMMARY_TTL = 300
BREAKDOWN_TTL = 3600
SNAP_TTL = 3600


def _scope_key(scope: dict | None) -> str:
    if not scope:
        return "global"
    parts = [f"{k}={scope[k]}" for k in sorted(scope)]
    return ",".join(parts)


def _response(data: dict, source: str, stale: bool = False, message: str | None = None) -> dict:
    payload = {"success": True, "data": data}
    payload["meta"] = {"source": source, "stale": stale}
    if message:
        payload["message"] = message
    return payload


def _build_summary_from_aggregates(db: Session, range_name: str) -> dict:
    dr = resolve_range(range_name)
    current_rows = db.query(DailyCostByService).filter(
        DailyCostByService.date >= dr.start, DailyCostByService.date <= dr.end
    ).all()
    previous_rows = db.query(DailyCostByService).filter(
        DailyCostByService.date >= dr.previous_start, DailyCostByService.date <= dr.previous_end
    ).all()

    current_by_service: dict[str, float] = {}
    previous_by_service: dict[str, float] = {}
    for row in current_rows:
        current_by_service[row.service] = current_by_service.get(row.service, 0.0) + float(row.cost or 0)
    for row in previous_rows:
        previous_by_service[row.service] = previous_by_service.get(row.service, 0.0) + float(row.cost or 0)

    total_cost = round(sum(current_by_service.values()), 2)
    previous_total = round(sum(previous_by_service.values()), 2)
    delta = round(total_cost - previous_total, 2)
    delta_pct = round((delta / previous_total) * 100, 2) if previous_total else 0.0
    if current_by_service:
        top_driver_name, top_driver_cost = max(current_by_service.items(), key=lambda item: item[1])
    else:
        top_driver_name, top_driver_cost = "No data", 0.0

    unallocated = db.query(CostByResource).filter(
        CostByResource.date >= dr.start,
        CostByResource.date <= dr.end,
        CostByResource.compartment_ocid.is_(None),
    ).count()
    latest = (
        db.query(CostSnapshot)
        .filter(CostSnapshot.name == f"cost_{range_name}")
        .order_by(desc(CostSnapshot.computed_at))
        .first()
    )
    return {
        "range": range_name,
        "total_cost": total_cost,
        "delta_vs_previous": delta,
        "delta_pct": delta_pct,
        "top_driver": {"name": top_driver_name, "cost": round(top_driver_cost, 2)},
        "unallocated": {"count": int(unallocated)},
        "last_computed_at": (latest.computed_at if latest else datetime.now(UTC)).isoformat(),
        "stale": False,
    }


def _breakdown_from_aggregates(db: Session, range_name: str, kind: str, limit: int) -> list[dict[str, Any]]:
    dr = resolve_range(range_name)
    if kind == "service":
        current_rows = (
            db.query(DailyCostByService)
            .filter(DailyCostByService.date >= dr.start, DailyCostByService.date <= dr.end)
            .all()
        )
        previous_rows = (
            db.query(DailyCostByService)
            .filter(DailyCostByService.date >= dr.previous_start, DailyCostByService.date <= dr.previous_end)
            .all()
        )
        current_map: dict[str, float] = {}
        previous_map: dict[str, float] = {}
        for row in current_rows:
            current_map[row.service] = current_map.get(row.service, 0.0) + float(row.cost or 0)
        for row in previous_rows:
            previous_map[row.service] = previous_map.get(row.service, 0.0) + float(row.cost or 0)
        total_current = sum(current_map.values()) or 0.0
        out = []
        for name in set(current_map) | set(previous_map):
            current = current_map.get(name, 0.0)
            previous = previous_map.get(name, 0.0)
            delta = current - previous
            delta_pct = (delta / previous) * 100 if previous else 0.0
            share = (current / total_current) * 100 if total_current else 0.0
            out.append(
                {
                    "service": name,
                    "name": name,
                    "current": round(current, 2),
                    "previous": round(previous, 2),
                    "delta_abs": round(delta, 2),
                    "delta_pct": round(delta_pct, 2),
                    "share_pct": round(share, 2),
                    "cost": round(current, 2),
                }
            )
        out.sort(key=lambda r: r["current"], reverse=True)
        return out[:limit]
    if kind == "compartment":
        current_rows = (
            db.query(CostByCompartment)
            .filter(CostByCompartment.date >= dr.start, CostByCompartment.date <= dr.end)
            .all()
        )
        previous_rows = (
            db.query(CostByCompartment)
            .filter(CostByCompartment.date >= dr.previous_start, CostByCompartment.date <= dr.previous_end)
            .all()
        )
        current_map: dict[str, float] = {}
        previous_map: dict[str, float] = {}
        name_map: dict[str, str] = {}
        for row in current_rows:
            key = row.compartment_ocid or "unknown"
            current_map[key] = current_map.get(key, 0.0) + float(row.cost or 0)
            name_map[key] = row.compartment_name or row.compartment_ocid or "Unknown"
        for row in previous_rows:
            key = row.compartment_ocid or "unknown"
            previous_map[key] = previous_map.get(key, 0.0) + float(row.cost or 0)
            if key not in name_map:
                name_map[key] = row.compartment_name or row.compartment_ocid or "Unknown"
        total_current = sum(current_map.values()) or 0.0
        out = []
        for key in set(current_map) | set(previous_map):
            current = current_map.get(key, 0.0)
            previous = previous_map.get(key, 0.0)
            delta = current - previous
            delta_pct = (delta / previous) * 100 if previous else 0.0
            share = (current / total_current) * 100 if total_current else 0.0
            out.append(
                {
                    "name": name_map.get(key, key),
                    "compartment_ocid": key,
                    "compartment_name": name_map.get(key, key),
                    "current": round(current, 2),
                    "previous": round(previous, 2),
                    "delta_abs": round(delta, 2),
                    "delta_pct": round(delta_pct, 2),
                    "share_pct": round(share, 2),
                    "cost": round(current, 2),
                }
            )
        out.sort(key=lambda r: r["current"], reverse=True)
        return out[:limit]
    current_rows = (
        db.query(CostByResource)
        .filter(CostByResource.date >= dr.start, CostByResource.date <= dr.end)
        .all()
    )
    previous_rows = (
        db.query(CostByResource)
        .filter(CostByResource.date >= dr.previous_start, CostByResource.date <= dr.previous_end)
        .all()
    )
    current_map: dict[str, dict[str, Any]] = {}
    previous_map: dict[str, float] = {}
    for row in current_rows:
        key = row.resource_ocid
        payload = current_map.setdefault(
            key,
            {
                "resource_ocid": row.resource_ocid,
                "resource_name": row.resource_name or row.resource_ocid,
                "service": row.service,
                "compartment_ocid": row.compartment_ocid,
                "current": 0.0,
            },
        )
        payload["current"] += float(row.cost or 0)
    for row in previous_rows:
        key = row.resource_ocid
        previous_map[key] = previous_map.get(key, 0.0) + float(row.cost or 0)
    total_current = sum(v["current"] for v in current_map.values()) or 0.0
    out = []
    for key, payload in current_map.items():
        current = payload["current"]
        previous = previous_map.get(key, 0.0)
        delta = current - previous
        delta_pct = (delta / previous) * 100 if previous else 0.0
        share = (current / total_current) * 100 if total_current else 0.0
        out.append(
            {
                "name": payload["resource_name"],
                "resource_ocid": key,
                "resource_name": payload["resource_name"],
                "service": payload["service"],
                "compartment_ocid": payload["compartment_ocid"],
                "current": round(current, 2),
                "previous": round(previous, 2),
                "delta_abs": round(delta, 2),
                "delta_pct": round(delta_pct, 2),
                "share_pct": round(share, 2),
                "cost": round(current, 2),
            }
        )
    out.sort(key=lambda r: r["current"], reverse=True)
    return out[:limit]


def _fallback_snapshot_data(db: Session, range_name: str, section: str) -> tuple[dict | list | None, bool]:
    snap_name = f"cost_{range_name}"
    snapshot = latest_snapshot(db, snap_name)
    if not snapshot or not snapshot.data:
        return None, False
    data = snapshot.data.get(section)
    if data is None:
        return None, False
    return data, True


def _legacy_snapshot_fallback(db: Session, section: str) -> tuple[dict | list | None, bool]:
    """
    Fallback for legacy snapshots that only populated total/by_service fields.
    Used to avoid blank UI while aggregate pipelines catch up.
    """
    row = (
        db.query(CostSnapshot)
        .filter(CostSnapshot.by_service.isnot(None))
        .order_by(desc(CostSnapshot.computed_at))
        .first()
    )
    if not row:
        return None, False
    if section == "summary":
        payload = {
            "range": "legacy_monthly",
            "total_cost": float(row.total or 0),
            "delta_vs_previous": 0.0,
            "delta_pct": 0.0,
            "top_driver": {"name": "No data", "cost": 0.0},
            "unallocated": {"count": 0},
            "last_computed_at": (row.computed_at or datetime.now(UTC)).isoformat(),
            "stale": True,
        }
        by_service = row.by_service or {}
        if by_service:
            top_name, top_cost = max(by_service.items(), key=lambda i: float(i[1] or 0))
            payload["top_driver"] = {"name": top_name, "cost": round(float(top_cost or 0), 2)}
        return payload, True
    if section == "by_service":
        by_service = row.by_service or {}
        items = [
            {
                "service": name,
                "name": name,
                "current": round(float(cost or 0), 2),
                "previous": 0.0,
                "delta_abs": round(float(cost or 0), 2),
                "delta_pct": 0.0,
                "share_pct": 0.0,
                "cost": round(float(cost or 0), 2),
            }
            for name, cost in by_service.items()
        ]
        total = sum(float(i["current"]) for i in items) or 0.0
        if total > 0:
            for item in items:
                item["share_pct"] = round((item["current"] / total) * 100, 2)
        items.sort(key=lambda r: r["current"], reverse=True)
        return items, True
    return None, False


@router.get("/summary")
async def cost_summary(
    range: str = Query("prev_month", pattern="^(prev_month|ytd|prev_year)$"),
    scope: str | None = Query(None),
    db: Session = Depends(get_db),
):
    scope_key = scope or "global"
    cache_key = f"cost:summary:{range}:{scope_key}"
    cached = cache_get(cache_key)
    if cached is not None:
        return _response(cached, source="cache")

    snapshot_summary, has_snapshot = _fallback_snapshot_data(db, range, "summary")
    if has_snapshot and isinstance(snapshot_summary, dict) and float(snapshot_summary.get("total_cost") or 0) > 0:
        payload = dict(snapshot_summary)
        payload["stale"] = True
        cache_set(cache_key, payload, SUMMARY_TTL)
        return _response(payload, source="snapshot", stale=True, message="Using last available snapshot")

    agg_summary = _build_summary_from_aggregates(db, range)
    if not agg_summary.get("total_cost"):
        legacy_summary, has_legacy = _legacy_snapshot_fallback(db, "summary")
        if has_legacy and isinstance(legacy_summary, dict):
            cache_set(cache_key, legacy_summary, SUMMARY_TTL)
            return _response(legacy_summary, source="legacy_snapshot", stale=True, message="Using last available snapshot")
        payload = dict(agg_summary)
        payload["stale"] = True
        payload["message"] = "Using last available snapshot"
        cache_set(cache_key, payload, SUMMARY_TTL)
        return _response(payload, source="aggregate", stale=True, message="Using last available snapshot")
    cache_set(cache_key, agg_summary, SUMMARY_TTL)
    return _response(agg_summary, source="aggregate")


@router.get("/by-service")
async def cost_by_service(
    range: str = Query("prev_month", pattern="^(prev_month|ytd|prev_year)$"),
    limit: int = Query(20, ge=1, le=200),
    scope: str | None = Query(None),
    db: Session = Depends(get_db),
):
    scope_key = scope or "global"
    cache_key = f"cost:service:{range}:{scope_key}:{limit}"
    cached = cache_get(cache_key)
    if cached is not None:
        return _response({"items": cached}, source="cache")
    snap, has_snap = _fallback_snapshot_data(db, range, "by_service")
    if has_snap and isinstance(snap, list) and len(snap) > 0:
        payload = snap[:limit]
        cache_set(cache_key, payload, BREAKDOWN_TTL)
        return _response({"items": payload}, source="snapshot", stale=True, message="Using last available snapshot")
    items = _breakdown_from_aggregates(db, range, "service", limit)
    if not items:
        legacy_items, has_legacy = _legacy_snapshot_fallback(db, "by_service")
        if has_legacy and isinstance(legacy_items, list):
            payload = legacy_items[:limit]
            cache_set(cache_key, payload, BREAKDOWN_TTL)
            return _response({"items": payload}, source="legacy_snapshot", stale=True, message="Using last available snapshot")
        return _response({"items": []}, source="aggregate", stale=True, message="Using last available snapshot")
    cache_set(cache_key, items, BREAKDOWN_TTL)
    return _response({"items": items}, source="aggregate")


@router.get("/by-compartment")
async def cost_by_compartment(
    range: str = Query("prev_month", pattern="^(prev_month|ytd|prev_year)$"),
    limit: int = Query(50, ge=1, le=500),
    scope: str | None = Query(None),
    db: Session = Depends(get_db),
):
    scope_key = scope or "global"
    cache_key = f"cost:compartment:{range}:{scope_key}:{limit}"
    cached = cache_get(cache_key)
    if cached is not None:
        return _response({"items": cached}, source="cache")
    snap, has_snap = _fallback_snapshot_data(db, range, "by_compartment")
    if has_snap and isinstance(snap, list):
        payload = snap[:limit]
        cache_set(cache_key, payload, BREAKDOWN_TTL)
        return _response({"items": payload}, source="snapshot", stale=True, message="Using last available snapshot")
    items = _breakdown_from_aggregates(db, range, "compartment", limit)
    if not items:
        legacy_items, has_legacy = _legacy_snapshot_fallback(db, "by_compartment")
        if has_legacy and isinstance(legacy_items, list):
            payload = legacy_items[:limit]
            cache_set(cache_key, payload, BREAKDOWN_TTL)
            return _response({"items": payload}, source="legacy_snapshot", stale=True, message="Using last available snapshot")
        return _response({"items": []}, source="aggregate", stale=True, message="No cost data available")
    cache_set(cache_key, items, BREAKDOWN_TTL)
    return _response({"items": items}, source="aggregate")


@router.get("/by-resource")
async def cost_by_resource(
    range: str = Query("prev_month", pattern="^(prev_month|ytd|prev_year)$"),
    limit: int = Query(50, ge=1, le=500),
    scope: str | None = Query(None),
    db: Session = Depends(get_db),
):
    scope_key = scope or "global"
    cache_key = f"cost:resource:{range}:{scope_key}:{limit}"
    cached = cache_get(cache_key)
    if cached is not None:
        return _response({"items": cached}, source="cache")
    snap, has_snap = _fallback_snapshot_data(db, range, "by_resource")
    if has_snap and isinstance(snap, list):
        payload = snap[:limit]
        cache_set(cache_key, payload, BREAKDOWN_TTL)
        return _response({"items": payload}, source="snapshot", stale=True, message="Using last available snapshot")
    items = _breakdown_from_aggregates(db, range, "resource", limit)
    if not items:
        return _response({"items": []}, source="aggregate", stale=True, message="Using last available snapshot")
    cache_set(cache_key, items, BREAKDOWN_TTL)
    return _response({"items": items}, source="aggregate")

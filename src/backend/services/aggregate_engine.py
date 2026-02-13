"""Phase 3 aggregate and snapshot computation services."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import desc
from sqlalchemy.orm import Session

from core.models import (
    CostByCompartment,
    CostByResource,
    CostSnapshot,
    DailyCostByService,
    LicenseCostTable,
    MonthlyCostByService,
    Resource,
    StorageWasteTable,
)
from core.redis_cache import cache_set


@dataclass
class DateRange:
    start: date
    end: date
    previous_start: date
    previous_end: date


def resolve_range(range_name: str) -> DateRange:
    today = datetime.now(UTC).date()
    if range_name == "ytd":
        start = date(today.year, 1, 1)
        end = today
    elif range_name == "prev_year":
        start = date(today.year - 1, 1, 1)
        end = date(today.year - 1, 12, 31)
    else:
        first_of_this_month = date(today.year, today.month, 1)
        end = first_of_this_month - timedelta(days=1)
        start = date(end.year, end.month, 1)
    span_days = (end - start).days + 1
    previous_end = start - timedelta(days=1)
    previous_start = previous_end - timedelta(days=span_days - 1)
    return DateRange(start=start, end=end, previous_start=previous_start, previous_end=previous_end)


def _to_decimal(value: Any) -> Decimal:
    try:
        return Decimal(str(value or 0))
    except Exception:
        return Decimal("0")


def _resource_cost(resource: Resource) -> Decimal:
    details = resource.details or {}
    for key in ("monthly_cost", "total_cost", "estimated_monthly_cost", "cost"):
        if key in details:
            return _to_decimal(details.get(key))
    return Decimal("0")


def _license_type(resource: Resource) -> tuple[str, str] | None:
    text = f"{resource.type or ''} {resource.name or ''}".lower()
    if "sql" in text:
        return ("sqlserver", "sql_server_license")
    if "windows" in text:
        return ("windows", "windows_license")
    if "oracle" in text:
        return ("oracle", "oracle_license")
    return None


def _waste_type(resource: Resource) -> str | None:
    status = (resource.status or "").lower()
    rtype = (resource.type or "").lower()
    if "backup" in rtype:
        return "backup"
    if "volume" in rtype and status in {"available", "detached", "stopped"}:
        return "unattached_volume"
    return None


def refresh_aggregates(db: Session, params: dict | None = None) -> dict:
    today = datetime.now(UTC).date()
    resources = db.query(Resource).all()

    service_totals_daily: dict[tuple[date, str], Decimal] = defaultdict(Decimal)
    service_totals_monthly: dict[tuple[date, str], Decimal] = defaultdict(Decimal)

    db.query(DailyCostByService).delete()
    db.query(MonthlyCostByService).delete()
    db.query(CostByCompartment).delete()
    db.query(CostByResource).delete()
    db.query(LicenseCostTable).delete()
    db.query(StorageWasteTable).delete()

    for resource in resources:
        cost_value = _resource_cost(resource)
        service = resource.type or "unknown"
        month_key = date(today.year, today.month, 1)
        service_totals_daily[(today, service)] += cost_value
        service_totals_monthly[(month_key, service)] += cost_value

        db.add(
            CostByResource(
                date=today,
                resource_ocid=resource.ocid,
                resource_name=resource.name,
                service=service,
                compartment_ocid=resource.compartment_id,
                cost=cost_value,
            )
        )
        db.add(
            CostByCompartment(
                date=today,
                compartment_ocid=resource.compartment_id,
                compartment_name=resource.compartment_id,
                service=service,
                cost=cost_value,
            )
        )

        license_info = _license_type(resource)
        if license_info:
            ltype, sku = license_info
            db.add(LicenseCostTable(date=today, license_type=ltype, sku=sku, cost=cost_value))

        waste = _waste_type(resource)
        if waste:
            db.add(
                StorageWasteTable(
                    date=today,
                    waste_type=waste,
                    resource_ocid=resource.ocid,
                    cost=cost_value,
                    details={"resource_name": resource.name, "status": resource.status},
                )
            )

    for (d, service), cost in service_totals_daily.items():
        db.add(DailyCostByService(date=d, service=service, cost=cost, currency="USD"))
    for (m, service), cost in service_totals_monthly.items():
        db.add(MonthlyCostByService(month=m, service=service, cost=cost))

    db.commit()
    return {
        "daily_rows": len(service_totals_daily),
        "monthly_rows": len(service_totals_monthly),
        "resource_rows": len(resources),
        "computed_at": datetime.now(UTC).isoformat(),
    }


def _build_summary(db: Session, range_name: str, scope: dict | None = None) -> dict:
    dr = resolve_range(range_name)
    start, end = dr.start, dr.end
    previous_start, previous_end = dr.previous_start, dr.previous_end

    current_rows = db.query(DailyCostByService).filter(DailyCostByService.date >= start, DailyCostByService.date <= end).all()
    previous_rows = db.query(DailyCostByService).filter(
        DailyCostByService.date >= previous_start, DailyCostByService.date <= previous_end
    ).all()

    current_by_service: dict[str, Decimal] = defaultdict(Decimal)
    previous_by_service: dict[str, Decimal] = defaultdict(Decimal)
    for row in current_rows:
        current_by_service[row.service] += _to_decimal(row.cost)
    for row in previous_rows:
        previous_by_service[row.service] += _to_decimal(row.cost)

    current_total = sum(current_by_service.values(), Decimal("0"))
    previous_total = sum(previous_by_service.values(), Decimal("0"))
    delta = current_total - previous_total
    delta_pct = float((delta / previous_total) * Decimal("100")) if previous_total else 0.0

    top_driver_name = "No data"
    top_driver_cost = Decimal("0")
    if current_by_service:
        top_driver_name, top_driver_cost = max(current_by_service.items(), key=lambda i: i[1])

    unallocated = db.query(CostByResource).filter(
        CostByResource.date >= start, CostByResource.date <= end, CostByResource.compartment_ocid.is_(None)
    ).count()

    return {
        "range": range_name,
        "scope": scope or {},
        "total_cost": float(round(current_total, 2)),
        "delta_vs_previous": float(round(delta, 2)),
        "delta_pct": round(delta_pct, 2),
        "top_driver": {"name": top_driver_name, "cost": float(round(top_driver_cost, 2))},
        "unallocated": {"count": int(unallocated)},
        "last_computed_at": datetime.now(UTC).isoformat(),
        "stale": False,
    }


def _serialize_breakdown(rows, value_attr: str = "cost"):
    out = []
    for row in rows:
        out.append(
            {
                "date": row.date.isoformat() if row.date else None,
                "service": getattr(row, "service", None),
                "cost": float(round(_to_decimal(getattr(row, value_attr, 0)), 2)),
                "resource_ocid": getattr(row, "resource_ocid", None),
                "resource_name": getattr(row, "resource_name", None),
                "compartment_ocid": getattr(row, "compartment_ocid", None),
                "compartment_name": getattr(row, "compartment_name", None),
            }
        )
    return out


def refresh_snapshot(db: Session, params: dict | None = None) -> dict:
    params = params or {}
    range_name = params.get("range", "prev_month")
    scope = params.get("scope", {})
    summary = _build_summary(db, range_name, scope)

    dr = resolve_range(range_name)
    by_service_rows = (
        db.query(DailyCostByService)
        .filter(DailyCostByService.date >= dr.start, DailyCostByService.date <= dr.end)
        .order_by(desc(DailyCostByService.cost))
        .limit(int(params.get("limit", 20)))
        .all()
    )
    by_compartment_rows = (
        db.query(CostByCompartment)
        .filter(CostByCompartment.date >= dr.start, CostByCompartment.date <= dr.end)
        .order_by(desc(CostByCompartment.cost))
        .limit(int(params.get("limit", 50)))
        .all()
    )
    by_resource_rows = (
        db.query(CostByResource)
        .filter(CostByResource.date >= dr.start, CostByResource.date <= dr.end)
        .order_by(desc(CostByResource.cost))
        .limit(int(params.get("limit", 50)))
        .all()
    )

    payload = {
        "summary": summary,
        "by_service": _serialize_breakdown(by_service_rows),
        "by_compartment": _serialize_breakdown(by_compartment_rows),
        "by_resource": _serialize_breakdown(by_resource_rows),
    }
    if float(payload["summary"].get("total_cost") or 0) <= 0:
        legacy = (
            db.query(CostSnapshot)
            .filter(CostSnapshot.period == "monthly", CostSnapshot.total > 0)
            .order_by(desc(CostSnapshot.computed_at))
            .first()
        )
        if legacy:
            payload["summary"]["total_cost"] = float(legacy.total or 0)
            payload["summary"]["stale"] = True
            payload["summary"]["last_computed_at"] = (legacy.computed_at or datetime.now(UTC)).isoformat()
            payload["summary"]["message"] = "Using last available snapshot"
            by_service = legacy.by_service or {}
            if by_service:
                top_name, top_cost = max(by_service.items(), key=lambda i: float(i[1] or 0))
                payload["summary"]["top_driver"] = {"name": top_name, "cost": float(round(float(top_cost or 0), 2))}
                if not payload["by_service"]:
                    payload["by_service"] = [
                        {
                            "date": None,
                            "service": name,
                            "cost": float(round(float(cost or 0), 2)),
                            "resource_ocid": None,
                            "resource_name": None,
                            "compartment_ocid": None,
                            "compartment_name": None,
                        }
                        for name, cost in by_service.items()
                    ]
                    payload["by_service"].sort(key=lambda r: r["cost"], reverse=True)

    snap_name = f"cost_{range_name}"
    snapshot_start = datetime.combine(dr.start, datetime.min.time(), tzinfo=UTC)
    snapshot_end = datetime.combine(dr.end, datetime.min.time(), tzinfo=UTC)
    snapshot = (
        db.query(CostSnapshot)
        .filter(CostSnapshot.period == range_name, CostSnapshot.start_date == snapshot_start)
        .first()
    )
    if snapshot:
        snapshot.name = snap_name
        snapshot.scope = scope
        snapshot.data = payload
        snapshot.computed_at = datetime.now(UTC)
        snapshot.end_date = snapshot_end
        snapshot.total = float(payload["summary"]["total_cost"])
        snapshot.by_service = {r["service"]: r["cost"] for r in payload["by_service"] if r.get("service")}
    else:
        snapshot = CostSnapshot(
            name=snap_name,
            scope=scope,
            data=payload,
            computed_at=datetime.now(UTC),
            period=range_name,
            start_date=snapshot_start,
            end_date=snapshot_end,
            total=float(payload["summary"]["total_cost"]),
            by_service={r["service"]: r["cost"] for r in payload["by_service"] if r.get("service")},
        )
        db.add(snapshot)
    db.commit()
    scope_key = "global"
    cache_set(f"snap:{snap_name}:{scope_key}", payload, 3600)
    cache_set(f"cost:summary:{range_name}:{scope_key}", payload["summary"], 300)
    cache_set(f"cost:service:{range_name}:{scope_key}:20", payload["by_service"][:20], 3600)
    cache_set(f"cost:compartment:{range_name}:{scope_key}:50", payload["by_compartment"][:50], 3600)
    cache_set(f"cost:resource:{range_name}:{scope_key}:50", payload["by_resource"][:50], 3600)
    return {"name": snap_name, "computed_at": snapshot.computed_at.isoformat()}


def latest_snapshot(db: Session, name: str) -> CostSnapshot | None:
    return db.query(CostSnapshot).filter(CostSnapshot.name == name).order_by(desc(CostSnapshot.computed_at)).first()

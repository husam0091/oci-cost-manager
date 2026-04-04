"""Cost API endpoints."""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from typing import Literal, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from api.schemas.costs import (
    AggregationPeriodModel,
    AggregationTotalsModel,
    BreakdownDataModel,
    BreakdownItemModel,
    CostsBreakdownResponse,
    CostsMoversResponse,
    MoversDataModel,
    MoversItemModel,
)
from core.cache import get_cached, set_cached, clear_cache, get_cache_info
from core.database import get_db
from core.models import AllocationRule, Compartment, CostSnapshot, Resource, ScanRun
from services import get_cost_calculator
from services.allocation import evaluate_allocation, load_enabled_rules
from api.utils.dates import (
    compute_previous_period,
    iso_date,
    parse_iso_datetime,
    parse_required_range,
)

router = APIRouter()

# Cache TTLs
COST_CACHE_TTL = 3600
AGG_CACHE_TTL = 600


def _is_usage_rate_limit_error(err: Exception) -> bool:
    text = str(err)
    return "TooManyRequests" in text or "'status': 429" in text or '"status": 429' in text


def _parse_cost_date(value: Optional[str], *, is_end: bool) -> datetime:
    return parse_iso_datetime(value, is_end=is_end, required=False)


def _normalize_workload_category(resource_type: Optional[str], sku_text: str) -> str:
    resource_type = (resource_type or "").lower()
    sku_text = sku_text.lower()

    if resource_type == "sql_server" or "sql server" in sku_text or "microsoft sql" in sku_text:
        return "sql_server"
    if resource_type == "windows_server" or "windows os" in sku_text:
        return "windows_server"
    if resource_type == "security_appliance" or "fortigate" in sku_text or "palo alto" in sku_text or "f5" in sku_text:
        return "security_appliance"
    if resource_type in {
        "block_volume",
        "boot_volume",
        "volume_backup",
        "boot_volume_backup",
        "nfs_file_system",
        "bucket",
    } or "backup" in sku_text or "block volume" in sku_text or "file storage" in sku_text:
        return "storage_and_backup"
    return "other"


def _compute_previous_window(start: datetime, end: datetime) -> tuple[datetime, datetime]:
    span = end - start
    prev_end = start
    prev_start = prev_end - span
    return prev_start, prev_end


def _safe_pct(delta: float, base: float) -> float:
    if not base:
        return 0.0
    return (delta / base) * 100.0


def _cache_key(prefix: str, **parts: object) -> str:
    ordered = "|".join(f"{k}={parts[k]}" for k in sorted(parts.keys()))
    return f"{prefix}|{ordered}"


def _get_allowed_resource_ids(db: Session, region: Optional[str]):
    """Return set of resource OCIDs for the given region, or None for no filter."""
    if not region or region == "all":
        return None
    from core.models import Resource as _Resource
    rows = db.query(_Resource.ocid).filter(_Resource.region == region).all()
    return {r.ocid for r in rows if r.ocid}


def _get_tag_value(details: dict, group_by: Literal["env", "team", "app"]) -> str:
    tags = (details.get("defined_tags") or {}) | (details.get("freeform_tags") or {})
    if group_by == "env":
        return tags.get("environment") or tags.get("env") or details.get("environment") or "Unallocated"
    if group_by == "team":
        return tags.get("owner_team") or tags.get("team") or details.get("owner_team") or "Unallocated"
    return tags.get("application") or tags.get("app") or details.get("application") or "Unallocated"


def _aggregate_resource_rows(
    rows: list[dict],
    group_by: Literal["compartment", "env", "team", "app", "resource"],
    resource_map: dict[str, Resource],
    rules: list[AllocationRule] | None = None,
    mapping_health: dict[str, float] | None = None,
    compartment_name_map: dict[str, str] | None = None,
) -> dict[str, float]:
    grouped: dict[str, float] = {}
    rules = rules or []
    compartment_name_map = compartment_name_map or {}
    mapping_health = mapping_health if mapping_health is not None else {"unowned_cost": 0.0, "low_confidence_cost": 0.0}
    for row in rows:
        rid = row.get("resource_id")
        total = float(row.get("total_cost") or 0.0)
        if total == 0:
            continue
        resource = resource_map.get(rid)
        if group_by == "compartment":
            comp_id = (resource.compartment_id if resource else None) or row.get("compartment_id")
            key = compartment_name_map.get(comp_id, row.get("compartment_name")) or comp_id or "Unknown"
        elif group_by == "resource":
            if resource and resource.name:
                key = resource.name
            elif rid:
                key = rid[-16:]
            else:
                key = "Unknown"
        else:
            allocation = evaluate_allocation(
                resource,
                rules,
                compartment_name=row.get("compartment_name"),
                sku_text=" ".join((s.get("sku_name") or "") for s in (row.get("skus") or [])),
            )
            key = getattr(allocation, group_by)
            if key == "Unallocated":
                mapping_health["unowned_cost"] = float(mapping_health.get("unowned_cost", 0.0)) + total
            if allocation.allocation_confidence == "low":
                mapping_health["low_confidence_cost"] = float(mapping_health.get("low_confidence_cost", 0.0)) + total
        grouped[key] = grouped.get(key, 0.0) + total
    return grouped


def _build_breakdown_items(
    current_map: dict[str, float],
    previous_map: dict[str, float],
    *,
    limit: int,
    min_share_pct: float,
) -> list[BreakdownItemModel]:
    total_current = float(sum(current_map.values()))
    if total_current == 0:
        return []

    names = set(current_map.keys()) | set(previous_map.keys())
    rows = []
    for name in names:
        current = float(current_map.get(name, 0.0))
        previous = float(previous_map.get(name, 0.0))
        delta_abs = current - previous
        share = (current / total_current) * 100.0 if total_current else 0.0
        rows.append(
            {
                "name": name,
                "current": current,
                "previous": previous,
                "delta_abs": delta_abs,
                "delta_pct": _safe_pct(delta_abs, previous),
                "share_pct": share,
            }
        )
    rows.sort(key=lambda x: x["current"], reverse=True)

    top = rows[:limit]
    remainder = rows[limit:]
    # No 0% noise outside top-N, but still preserve totals by collapsing into Other.
    remainder_filtered = [r for r in remainder if r["share_pct"] >= min_share_pct or r["current"] > 0 or r["previous"] > 0]
    excluded = [r for r in remainder if r not in remainder_filtered]
    collapsed = remainder_filtered + excluded

    items = [
        BreakdownItemModel(
            name=r["name"],
            current=round(r["current"], 2),
            previous=round(r["previous"], 2),
            delta_abs=round(r["delta_abs"], 2),
            delta_pct=round(r["delta_pct"], 2),
            share_pct=round(r["share_pct"], 2),
        )
        for r in top
    ]

    if collapsed:
        other_current = sum(r["current"] for r in collapsed)
        other_previous = sum(r["previous"] for r in collapsed)
        other_delta = other_current - other_previous
        other_share = (other_current / total_current * 100.0) if total_current else 0.0
        items.append(
            BreakdownItemModel(
                name="Other",
                current=round(other_current, 2),
                previous=round(other_previous, 2),
                delta_abs=round(other_delta, 2),
                delta_pct=round(_safe_pct(other_delta, other_previous), 2),
                share_pct=round(other_share, 2),
            )
        )
    return items


@router.get("")
async def get_costs(
    period: str = Query("monthly", description="Period: monthly or yearly"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    refresh: bool = Query(False, description="Force refresh from OCI API"),
):
    """Get cost summary for the specified period. Uses cache by default."""
    try:
        # Parse dates
        if start_date:
            start = datetime.fromisoformat(start_date)
        else:
            today = datetime.now(UTC)
            if period == "yearly":
                start = today.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            else:
                start = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        if end_date:
            end = datetime.fromisoformat(end_date)
        else:
            end = datetime.now(UTC)
        
        # Cache key based on period and date
        cache_key = f"costs_{period}_{start.strftime('%Y%m%d')}"
        
        # Check cache first (unless refresh requested)
        if not refresh:
            cached = get_cached(cache_key)
            if cached is not None:
                return {
                    "success": True,
                    "data": cached,
                    "cached": True,
                }
        
        # Fetch from OCI API
        calculator = get_cost_calculator()
        
        def fetch_costs():
            return calculator.get_costs_by_service(start, end)
        
        # Run in thread pool with timeout
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as executor:
            try:
                timeout_sec = 120.0 if refresh else 10.0
                costs = await asyncio.wait_for(
                    loop.run_in_executor(executor, fetch_costs),
                    timeout=timeout_sec
                )
            except asyncio.TimeoutError:
                # Return cached data if available, even if expired
                cached = get_cached(cache_key)
                if cached:
                    return {
                        "success": True,
                        "data": cached,
                        "cached": True,
                        "warning": "API timeout - showing cached data",
                    }
                costs = {}
        
        result = {
            "period": period,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "total": sum(costs.values()),
            "by_service": costs,
        }
        
        # Cache the result
        set_cached(cache_key, result, COST_CACHE_TTL)
        
        return {
            "success": True,
            "data": result,
            "cached": False,
        }
    except Exception as e:
        import traceback
        print(f"Cost API error: {str(e)}")
        traceback.print_exc()
        # Try to return cached data on error
        cached = get_cached(f"costs_{period}")
        if cached:
            return {
                "success": True,
                "data": cached,
                "cached": True,
                "warning": f"API error - showing cached data: {str(e)}",
            }
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/by-resource")
async def get_costs_by_resource(
    compartment_id: Optional[str] = Query(None, description="Filter by compartment"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    include_skus: bool = Query(True, description="Include SKU line items per resource"),
    region: Optional[str] = Query(None, description="Filter to a specific OCI region"),
    db: Session = Depends(get_db),
):
    """Get costs grouped by resource."""
    cache_key = f"costs_by_resource_{compartment_id or 'all'}_{start_date or 'auto'}_{end_date or 'auto'}_{'skus' if include_skus else 'noskus'}_{region or 'all'}"
    try:
        calculator = get_cost_calculator()
        region_filter = region if (region and region != "all") else None

        # Parse dates. End date is treated inclusively for date-only inputs.
        start = _parse_cost_date(start_date, is_end=False)
        end = _parse_cost_date(end_date, is_end=True)
        if end <= start:
            raise HTTPException(status_code=422, detail="end_date must be after start_date")

        resource_costs = calculator.get_costs_by_resource(
            start,
            end,
            compartment_id,
            include_skus=include_skus,
            region=region_filter,
        )

        # Normalize workload categories in backend so frontend does not duplicate SKU mapping.
        resource_ids = [r.get("resource_id") for r in resource_costs if r.get("resource_id")]
        resource_rows = (
            db.query(Resource.ocid, Resource.type)
            .filter(Resource.ocid.in_(resource_ids))
            .all()
            if resource_ids
            else []
        )
        resource_type_map = {ocid: rtype for ocid, rtype in resource_rows}
        for item in resource_costs:
            sku_text = " ".join((s.get("sku_name") or "") for s in (item.get("skus") or []))
            item["resource_type"] = resource_type_map.get(item.get("resource_id"))
            item["normalized_workload_category"] = _normalize_workload_category(item.get("resource_type"), sku_text)
        
        # Sort by cost descending
        resource_costs.sort(key=lambda x: x.get("total_cost", 0), reverse=True)
        
        result = {
            "success": True,
            "data": resource_costs,
            "meta": {
                "total": len(resource_costs),
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
                "end_date_inclusive": bool(end_date and "T" not in end_date),
                "include_skus": include_skus,
            },
        }
        set_cached(cache_key, result, COST_CACHE_TTL)
        return result
    except HTTPException:
        raise
    except Exception as e:
        cached = get_cached(cache_key)
        if cached is not None:
            cached["cached"] = True
            cached["warning"] = f"Live OCI usage unavailable, showing cached data: {str(e)}"
            return cached
        if _is_usage_rate_limit_error(e):
            raise HTTPException(status_code=503, detail="OCI Usage API is rate-limited (429). Retry shortly.")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/databases")
async def get_database_costs(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
):
    """Get costs specifically for database services."""
    cache_key = f"costs_databases_{start_date or 'auto'}_{end_date or 'auto'}"
    try:
        calculator = get_cost_calculator()
        
        # Parse dates. End date is treated inclusively for date-only inputs.
        start = _parse_cost_date(start_date, is_end=False)
        end = _parse_cost_date(end_date, is_end=True)
        if end <= start:
            raise HTTPException(status_code=422, detail="end_date must be after start_date")
        
        db_costs = calculator.get_database_costs(start, end)
        
        result = {
            "success": True,
            "data": {
                "period": {
                    "start_date": start.isoformat(),
                    "end_date": end.isoformat(),
                },
                **db_costs,
            },
        }
        set_cached(cache_key, result, COST_CACHE_TTL)
        return result
    except HTTPException:
        raise
    except Exception as e:
        cached = get_cached(cache_key)
        if cached is not None:
            cached["cached"] = True
            return cached
        if _is_usage_rate_limit_error(e):
            raise HTTPException(status_code=503, detail="OCI Usage API rate-limited — please retry shortly")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary")
async def get_costs_summary(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    region: Optional[str] = Query(None, description="Filter to a specific OCI region"),
    db: Session = Depends(get_db),
):
    """Decision-driving cost summary with period deltas and governance signals."""
    start = _parse_cost_date(start_date, is_end=False)
    end = _parse_cost_date(end_date, is_end=True)
    if end <= start:
        raise HTTPException(status_code=422, detail="end_date must be after start_date")
    region_filter = region if (region and region != "all") else None
    cache_key = _cache_key(
        "agg_summary",
        start=iso_date(start),
        end=iso_date(end - timedelta(days=1)),
        region=region or "",
    )
    cached = get_cached(cache_key)
    if cached is not None:
        return cached

    calculator = get_cost_calculator()
    prev_start, prev_end = _compute_previous_window(start, end)

    def _fetch_summary():
        return (
            calculator.get_costs_by_service(start, end, region=region_filter),
            calculator.get_costs_by_service(prev_start, prev_end, region=region_filter),
            calculator.get_costs_by_resource(start, end, include_skus=False, region=region_filter),
        )

    try:
        loop = asyncio.get_event_loop()
        current_by_service, previous_by_service, resource_rows = await asyncio.wait_for(
            loop.run_in_executor(None, _fetch_summary), timeout=70.0
        )
    except asyncio.TimeoutError:
        raise HTTPException(status_code=503, detail="OCI Usage API timed out")
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"OCI Usage API unavailable: {type(exc).__name__}")

    current_total = float(sum(current_by_service.values()))
    previous_total = float(sum(previous_by_service.values()))
    delta_abs = current_total - previous_total
    delta_pct = _safe_pct(delta_abs, previous_total)

    service_rows = []
    for item in _build_breakdown_items(current_by_service, previous_by_service, limit=8, min_share_pct=0.0):
        service_rows.append(
            {
                "entity": item.name,
                "current": item.current,
                "previous": item.previous,
                "delta_abs": item.delta_abs,
                "delta_pct": item.delta_pct,
                "share": item.share_pct,
            }
        )
    top_driver = service_rows[0] if service_rows else {"entity": "N/A", "current": 0, "previous": 0, "delta_abs": 0, "delta_pct": 0, "share": 0}
    biggest_mover = max(service_rows, key=lambda r: abs(r["delta_abs"])) if service_rows else top_driver
    resource_ids = [r.get("resource_id") for r in resource_rows if r.get("resource_id")]
    resource_types = {
        ocid: rtype for ocid, rtype in db.query(Resource.ocid, Resource.type).filter(Resource.ocid.in_(resource_ids)).all()
    } if resource_ids else {}
    unallocated_count = sum(1 for r in resource_rows if not resource_types.get(r.get("resource_id")))
    unallocated_pct = (unallocated_count / len(resource_rows) * 100.0) if resource_rows else 0.0

    last_scan = db.query(ScanRun).order_by(ScanRun.started_at.desc()).first()
    last_snapshot = db.query(CostSnapshot).order_by(CostSnapshot.end_date.desc()).first()
    result = {
        "success": True,
        "data": {
            "total": current_total,
            "previous_total": previous_total,
            "delta_abs": delta_abs,
            "delta_pct": delta_pct,
            "top_driver": top_driver,
            "biggest_mover": biggest_mover,
            "unallocated": {"pct": unallocated_pct, "count": unallocated_count},
            "freshness": {
                "last_scan_at": last_scan.finished_at.isoformat() if last_scan and last_scan.finished_at else None,
                "last_cost_refresh_at": last_snapshot.end_date.isoformat() if last_snapshot and last_snapshot.end_date else None,
                "scan_status": last_scan.status if last_scan else "unknown",
            },
            "period": {
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
                "previous_start_date": prev_start.isoformat(),
                "previous_end_date": prev_end.isoformat(),
            },
        },
    }
    set_cached(cache_key, result, AGG_CACHE_TTL)
    return result


@router.get("/breakdown", response_model=CostsBreakdownResponse, response_model_exclude_none=True)
async def get_costs_breakdown(
    group_by: Literal["service", "compartment", "region", "top_resources", "sku"] = Query("service"),
    start_date: str = Query(...),
    end_date: str = Query(...),
    compare: str = Query("previous"),
    limit: int = Query(8, ge=1, le=50),
    min_share_pct: float = Query(0.5, ge=0.0, le=100.0),
    region: Optional[str] = Query(None, description="Filter to a specific OCI region"),
    db: Session = Depends(get_db),
):
    """Aggregated breakdown contract: top-N + Other with deterministic schema."""
    cache_key = _cache_key(
        "agg_breakdown",
        group_by=group_by,
        start=start_date,
        end=end_date,
        compare=compare,
        limit=limit,
        min_share_pct=min_share_pct,
        region=region or "",
    )
    cached = get_cached(cache_key)
    if cached is not None:
        return CostsBreakdownResponse(**cached)

    if compare != "previous":
        raise HTTPException(status_code=422, detail="compare must be 'previous'")

    region_filter = region if (region and region != "all") else None
    calculator = get_cost_calculator()
    start, end_exclusive, days = parse_required_range(start_date, end_date)
    prev_start, prev_end = compute_previous_period(start, end_exclusive)

    def _fetch_breakdown():
        if group_by == "service":
            return (
                calculator.get_costs_by_service(start, end_exclusive, region=region_filter),
                calculator.get_costs_by_service(prev_start, prev_end, region=region_filter),
            )
        if group_by == "compartment":
            return (
                calculator.get_costs_by_compartment(start, end_exclusive, region=region_filter),
                calculator.get_costs_by_compartment(prev_start, prev_end, region=region_filter),
            )
        if group_by == "region":
            return (
                calculator.get_costs_by_region(start, end_exclusive),
                calculator.get_costs_by_region(prev_start, prev_end),
            )
        if group_by == "sku":
            return (
                calculator.get_costs_by_sku(start, end_exclusive, region=region_filter),
                calculator.get_costs_by_sku(prev_start, prev_end, region=region_filter),
            )
        if group_by == "top_resources":
            # Fetch more than the display limit so we capture network, DB, etc.
            raw_limit = max(limit * 5, 50)
            return (
                calculator.get_top_resource_costs_raw(start, end_exclusive, region=region_filter, limit=raw_limit),
                calculator.get_top_resource_costs_raw(prev_start, prev_end, region=region_filter, limit=raw_limit),
            )
        return (
            calculator.get_costs_by_service(start, end_exclusive, region=region_filter),
            calculator.get_costs_by_service(prev_start, prev_end, region=region_filter),
        )

    try:
        loop = asyncio.get_event_loop()
        current, previous = await asyncio.wait_for(
            loop.run_in_executor(None, _fetch_breakdown), timeout=70.0
        )
    except (asyncio.TimeoutError, Exception) as exc:
        stale = get_cached(cache_key)
        if stale is not None:
            return CostsBreakdownResponse(**stale)
        if isinstance(exc, asyncio.TimeoutError):
            raise HTTPException(status_code=503, detail="OCI Usage API timed out")
        raise HTTPException(status_code=503, detail=f"OCI Usage API unavailable: {type(exc).__name__}")

    # For top_resources, resolve raw rows to {name: cost} using local DB names
    if group_by == "top_resources":
        cur_rows, prev_rows = current, previous
        all_rids = list({r.get("resource_id") for r in cur_rows + prev_rows if r.get("resource_id")})
        name_map = {}
        if all_rids:
            from core.models import Resource as _Res
            db_rows = db.query(_Res.ocid, _Res.name, _Res.type, _Res.compartment_id).filter(_Res.ocid.in_(all_rids)).all()
            comp_ids = {r.compartment_id for r in db_rows if r.compartment_id}
            comp_names = {}
            if comp_ids:
                comp_names = dict(db.query(Compartment.id, Compartment.name).filter(Compartment.id.in_(comp_ids)).all())
            for r in db_rows:
                comp = comp_names.get(r.compartment_id, "")
                label = r.name or r.ocid[-20:]
                if comp:
                    label = f"{label} ({comp})"
                name_map[r.ocid] = label

            # For unmatched OCIDs (e.g. mysqlinstance), try matching to parent DB systems
            unmatched = [rid for rid in all_rids if rid not in name_map and rid.startswith("ocid1.")]
            if unmatched:
                # Build lookup: region -> list of mysql DB system names
                mysql_resources = db.query(_Res.ocid, _Res.name, _Res.compartment_id).filter(_Res.type == "mysql").all()
                mysql_by_region = {}
                for mr in mysql_resources:
                    parts = mr.ocid.split(".")
                    if len(parts) >= 4:
                        rgn = parts[3]
                        mysql_by_region.setdefault(rgn, []).append(mr)

                _ocid_type_labels = {
                    "mysqlinstance": "MySQL",
                    "mysqldbsystem": "MySQL DB",
                    "opensearchcluster": "OpenSearch",
                    "dbsystem": "Oracle DB",
                    "autonomousdatabase": "Autonomous DB",
                    "filesystem": "File System",
                    "loadbalancer": "Load Balancer",
                    "networkloadbalancer": "Network LB",
                    "instance": "Compute",
                    "bootvolume": "Boot Volume",
                    "volume": "Block Volume",
                    "bucket": "Object Storage",
                }
                _counter: dict[str, int] = {}
                for rid in unmatched:
                    parts = rid.split(".")
                    ocid_type = parts[1] if len(parts) >= 2 else "unknown"
                    ocid_region = parts[3] if len(parts) >= 4 else ""
                    friendly = _ocid_type_labels.get(ocid_type, ocid_type.replace("_", " ").title())

                    # Try matching mysqlinstance to a named mysql DB system in same region
                    if ocid_type == "mysqlinstance" and ocid_region in mysql_by_region:
                        candidates = mysql_by_region[ocid_region]
                        idx = _counter.get(ocid_region + "_mysql", 0)
                        if idx < len(candidates):
                            mr = candidates[idx]
                            comp = comp_names.get(mr.compartment_id, "")
                            label = mr.name or friendly
                            if comp:
                                label = f"{label} ({comp})"
                            name_map[rid] = label
                            _counter[ocid_region + "_mysql"] = idx + 1
                            continue

                    region_label = ocid_region.replace("_", "-") if ocid_region else ""
                    short_id = parts[-1][:8] if parts else rid[-8:]
                    label = f"{friendly} {short_id}"
                    if region_label:
                        label = f"{label} ({region_label})"
                    name_map[rid] = label

        current = {}
        for r in cur_rows:
            rid = r.get("resource_id") or "Unknown"
            label = name_map.get(rid, rid[-24:])
            current[label] = current.get(label, 0.0) + float(r.get("total_cost") or 0)
        previous = {}
        for r in prev_rows:
            rid = r.get("resource_id") or "Unknown"
            label = name_map.get(rid, rid[-24:])
            previous[label] = previous.get(label, 0.0) + float(r.get("total_cost") or 0)

    items = _build_breakdown_items(current, previous, limit=limit, min_share_pct=min_share_pct)
    response = CostsBreakdownResponse(
        success=True,
        data=BreakdownDataModel(
            group_by=group_by,
            period=AggregationPeriodModel(
                start_date=iso_date(start),
                end_date=iso_date(end_exclusive - timedelta(days=1)),
                days=days,
            ),
            totals=AggregationTotalsModel(
                current=round(float(sum(current.values())), 2),
                previous=round(float(sum(previous.values())), 2),
            ),
            items=items,
            mapping_health=None,
        ),
    )
    set_cached(cache_key, response.model_dump(), AGG_CACHE_TTL)
    return response


@router.get("/movers", response_model=CostsMoversResponse)
async def get_costs_movers(
    group_by: Literal["service", "compartment", "resource"] = Query("service"),
    start_date: str = Query(...),
    end_date: str = Query(...),
    compare: str = Query("previous"),
    limit: int = Query(20, ge=1, le=200),
    direction: Literal["up", "down", "both"] = Query("both"),
    region: Optional[str] = Query(None, description="Filter to a specific OCI region"),
    db: Session = Depends(get_db),
):
    """Delta-based movers for what-changed decisions."""
    cache_key = _cache_key(
        "agg_movers",
        group_by=group_by,
        start=start_date,
        end=end_date,
        compare=compare,
        limit=limit,
        direction=direction,
        region=region or "",
    )
    cached = get_cached(cache_key)
    if cached is not None:
        return CostsMoversResponse(**cached)

    if compare != "previous":
        raise HTTPException(status_code=422, detail="compare must be 'previous'")

    region_filter = region if (region and region != "all") else None
    calculator = get_cost_calculator()
    start, end_exclusive, days = parse_required_range(start_date, end_date)
    prev_start, prev_end = compute_previous_period(start, end_exclusive)

    def _fetch_movers():
        if group_by == "service":
            return (
                calculator.get_costs_by_service(start, end_exclusive, region=region_filter),
                calculator.get_costs_by_service(prev_start, prev_end, region=region_filter),
                [],
                [],
            )
        return (
            {},
            {},
            calculator.get_costs_by_resource(start, end_exclusive, include_skus=False, region=region_filter),
            calculator.get_costs_by_resource(prev_start, prev_end, include_skus=False, region=region_filter),
        )

    try:
        loop = asyncio.get_event_loop()
        _cur_svc, _prev_svc, _cur_rows, _prev_rows = await asyncio.wait_for(
            loop.run_in_executor(None, _fetch_movers), timeout=70.0
        )
    except (asyncio.TimeoutError, Exception) as exc:
        stale = get_cached(cache_key)
        if stale is not None:
            return CostsMoversResponse(**stale)
        if isinstance(exc, asyncio.TimeoutError):
            raise HTTPException(status_code=503, detail="OCI Usage API timed out")
        raise HTTPException(status_code=503, detail=f"OCI Usage API unavailable: {type(exc).__name__}")

    items: list[MoversItemModel] = []
    if group_by == "service":
        current, previous = _cur_svc, _prev_svc
        names = set(current.keys()) | set(previous.keys())
        for name in names:
            cur = float(current.get(name, 0.0))
            prev = float(previous.get(name, 0.0))
            delta = cur - prev
            items.append(
                MoversItemModel(
                    name=name,
                    current=round(cur, 2),
                    previous=round(prev, 2),
                    delta_abs=round(delta, 2),
                    delta_pct=round(_safe_pct(delta, prev), 2),
                )
            )
    else:
        current_rows, previous_rows = _cur_rows, _prev_rows
        prev_by_resource = {r.get("resource_id"): float(r.get("total_cost") or 0.0) for r in previous_rows}
        resource_ids = list({
            *(r.get("resource_id") for r in current_rows if r.get("resource_id")),
            *(r.get("resource_id") for r in previous_rows if r.get("resource_id")),
        })
        resources = db.query(Resource).filter(Resource.ocid.in_(resource_ids)).all() if resource_ids else []
        resource_map = {r.ocid: r for r in resources}

        if group_by == "compartment":
            current_grouped = _aggregate_resource_rows(current_rows, "compartment", resource_map)
            previous_grouped = _aggregate_resource_rows(previous_rows, "compartment", resource_map)
            names = set(current_grouped.keys()) | set(previous_grouped.keys())
            for name in names:
                cur = float(current_grouped.get(name, 0.0))
                prev = float(previous_grouped.get(name, 0.0))
                delta = cur - prev
                items.append(
                    MoversItemModel(
                        name=name,
                        current=round(cur, 2),
                        previous=round(prev, 2),
                        delta_abs=round(delta, 2),
                        delta_pct=round(_safe_pct(delta, prev), 2),
                    )
                )
        else:
            # Resolve compartment names from DB
            all_comp_ids = {r.compartment_id for r in resources if r.compartment_id}
            comp_name_map = {}
            if all_comp_ids:
                comp_name_map = dict(db.query(Compartment.id, Compartment.name).filter(Compartment.id.in_(all_comp_ids)).all())

            # Build a type label map for unmatched OCIDs
            _type_labels = {
                "mysqlinstance": "MySQL", "opensearchcluster": "OpenSearch",
                "filesystem": "File System", "loadbalancer": "Load Balancer",
                "bootvolume": "Boot Volume", "volume": "Block Volume",
                "bucket": "Object Storage", "dbsystem": "Oracle DB",
            }

            for row in current_rows:
                rid = row.get("resource_id")
                cur = float(row.get("total_cost") or 0.0)
                prev = float(prev_by_resource.get(rid, 0.0))
                delta = cur - prev
                resource = resource_map.get(rid)
                if resource and resource.name:
                    name = resource.name
                    rtype = resource.type
                    comp = comp_name_map.get(resource.compartment_id, "")
                elif rid and rid.startswith("ocid1."):
                    parts = rid.split(".")
                    ocid_type = parts[1] if len(parts) >= 2 else "unknown"
                    short_id = parts[-1][:8] if parts else rid[-8:]
                    name = f"{_type_labels.get(ocid_type, ocid_type)} {short_id}"
                    rtype = _type_labels.get(ocid_type, ocid_type)
                    comp = parts[3].replace("_", "-") if len(parts) >= 4 else ""
                else:
                    name = rid[-16:] if rid else "Unknown"
                    rtype = None
                    comp = ""
                items.append(
                    MoversItemModel(
                        name=name,
                        current=round(cur, 2),
                        previous=round(prev, 2),
                        delta_abs=round(delta, 2),
                        delta_pct=round(_safe_pct(delta, prev), 2),
                        type=rtype,
                        compartment_name=comp or None,
                    )
                )

    if direction == "up":
        filtered = [i for i in items if i.delta_abs > 0]
        filtered.sort(key=lambda x: (-x.delta_abs, x.name))
    elif direction == "down":
        filtered = [i for i in items if i.delta_abs < 0]
        filtered.sort(key=lambda x: (x.delta_abs, x.name))
    else:
        filtered = list(items)
        filtered.sort(key=lambda x: (-abs(x.delta_abs), x.name))

    response = CostsMoversResponse(
        success=True,
        data=MoversDataModel(
            group_by=group_by,
            period=AggregationPeriodModel(
                start_date=iso_date(start),
                end_date=iso_date(end_exclusive - timedelta(days=1)),
                days=days,
            ),
            items=filtered[:limit],
        ),
    )
    set_cached(cache_key, response.model_dump(), AGG_CACHE_TTL)
    return response


@router.get("/insights")
async def get_insights(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Generate concise actionable insights for governance dashboards."""
    if not start_date or not end_date:
        start = _parse_cost_date(start_date, is_end=False)
        end_exclusive = _parse_cost_date(end_date, is_end=True)
        start_date = iso_date(start)
        end_date = iso_date(end_exclusive - timedelta(days=1))

    summary = (await get_costs_summary(start_date=start_date, end_date=end_date, db=db))["data"]
    service_breakdown_res = await get_costs_breakdown(
        group_by="service",
        start_date=start_date,
        end_date=end_date,
        compare="previous",
        limit=8,
        min_share_pct=0.0,
        db=db,
    )
    service_breakdown = service_breakdown_res.data.items
    insights = []
    if summary["delta_abs"] > 0:
        insights.append({
            "title": "Spend increased versus previous period",
            "impact": round(summary["delta_abs"], 2),
            "reason": f"Overall cost is up {summary['delta_pct']:.2f}%",
            "drilldown": {"path": "/costs", "filters": {"group_by": "service"}},
        })
    if summary["unallocated"]["pct"] > 5:
        insights.append({
            "title": "Low-confidence / unallocated mapping is elevated",
            "impact": summary["unallocated"]["count"],
            "reason": f"{summary['unallocated']['pct']:.2f}% of resources are unmapped",
            "drilldown": {"path": "/resources", "filters": {"tag_missing": True}},
        })
    if service_breakdown:
        top = max(service_breakdown, key=lambda x: x.delta_abs)
        insights.append({
            "title": f"Top service mover: {top.name}",
            "impact": round(top.delta_abs, 2),
            "reason": f"Delta {top.delta_pct:.2f}% with {top.share_pct:.2f}% share",
            "drilldown": {"path": "/costs", "filters": {"group_by": "service", "entity": top.name}},
        })
    if summary["freshness"]["scan_status"] == "failed":
        insights.append({
            "title": "Scan health alert",
            "impact": 0,
            "reason": "Latest scan finished with failed status",
            "drilldown": {"path": "/settings", "filters": {"tab": "scan"}},
        })

    return {"success": True, "data": insights[:5], "meta": {"count": min(len(insights), 5)}}


@router.get("/daily")
async def get_daily_costs(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD), defaults to first of current month"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD), defaults to today"),
    region: Optional[str] = Query(None, description="Filter to a specific OCI region"),
    db: Session = Depends(get_db),
):
    """Daily cost breakdown by service - mirrors OCI Cost Analysis daily view."""
    today = datetime.now(UTC)
    start = _parse_cost_date(start_date, is_end=False) if start_date else today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    end = _parse_cost_date(end_date, is_end=True) if end_date else today
    if end <= start:
        raise HTTPException(status_code=422, detail="end_date must be after start_date")
    region_filter = region if (region and region != "all") else None
    cache_key = _cache_key("daily_costs", start=iso_date(start), end=iso_date(end), region=region or "")
    cached = get_cached(cache_key)
    if cached is not None:
        return {"success": True, "data": cached, "cached": True}
    try:
        calculator = get_cost_calculator()
        loop = asyncio.get_event_loop()
        daily = await asyncio.wait_for(
            loop.run_in_executor(None, lambda: calculator.get_daily_costs(start, end, region=region_filter)),
            timeout=70.0,
        )
        mtd_total = round(sum(d["total"] for d in daily), 2)
        result = {
            "period": {"start_date": iso_date(start), "end_date": iso_date(end)},
            "mtd_total": mtd_total,
            "days": daily,
        }
        set_cached(cache_key, result, COST_CACHE_TTL)
        return {"success": True, "data": result, "cached": False}
    except Exception as exc:
        cached = get_cached(cache_key)
        if cached is not None:
            return {"success": True, "data": cached, "cached": True, "warning": str(exc)}
        if _is_usage_rate_limit_error(exc):
            raise HTTPException(status_code=503, detail="OCI Usage API rate-limited (429). Retry shortly.")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/by-region")
async def get_costs_by_region(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
):
    """Get total spend broken down by OCI region for cross-region comparison."""
    start = _parse_cost_date(start_date, is_end=False)
    end = _parse_cost_date(end_date, is_end=True)
    if end <= start:
        raise HTTPException(status_code=422, detail="end_date must be after start_date")
    cache_key = _cache_key("costs_by_region", start=iso_date(start), end=iso_date(end))
    cached = get_cached(cache_key)
    if cached is not None:
        return {"success": True, "data": cached, "cached": True}
    try:
        calculator = get_cost_calculator()
        loop = asyncio.get_event_loop()
        by_region = await asyncio.wait_for(
            loop.run_in_executor(None, lambda: calculator.get_costs_by_region(start, end)),
            timeout=70.0,
        )
        total = sum(by_region.values())
        regions = sorted(
            [{"region": r, "total": round(v, 2), "share_pct": round(v / total * 100, 2) if total else 0}
             for r, v in by_region.items()],
            key=lambda x: -x["total"],
        )
        result = {"total": round(total, 2), "regions": regions, "period": {"start_date": iso_date(start), "end_date": iso_date(end)}}
        set_cached(cache_key, result, AGG_CACHE_TTL)
        return {"success": True, "data": result, "cached": False}
    except asyncio.TimeoutError:
        raise HTTPException(status_code=503, detail="OCI Usage API timed out")
    except Exception as exc:
        cached = get_cached(cache_key)
        if cached is not None:
            return {"success": True, "data": cached, "cached": True, "warning": str(exc)}
        raise HTTPException(status_code=503, detail=f"OCI Usage API unavailable: {type(exc).__name__}")


@router.get("/trends")
async def get_cost_trends(
    months: int = Query(6, description="Number of months to include"),
):
    """Get monthly cost trends."""
    try:
        calculator = get_cost_calculator()
        trends = calculator.get_cost_trends(months)

        return {
            "success": True,
            "data": trends,
            "meta": {"months": months},
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/top-resources")
async def get_top_resources(
    limit: int = Query(10, description="Number of top resources to return"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
):
    """Get top N most expensive resources."""
    try:
        calculator = get_cost_calculator()
        
        # Parse dates
        today = datetime.now(UTC)
        start = datetime.fromisoformat(start_date) if start_date else today.replace(day=1)
        end = datetime.fromisoformat(end_date) if end_date else today
        
        resource_costs = calculator.get_costs_by_resource(start, end)
        
        # Sort and limit
        resource_costs.sort(key=lambda x: x.get("total_cost", 0), reverse=True)
        top_resources = resource_costs[:limit]
        
        return {
            "success": True,
            "data": top_resources,
            "meta": {
                "total_resources": len(resource_costs),
                "showing": len(top_resources),
            },
        }
    except Exception as e:
        if _is_usage_rate_limit_error(e):
            return {
                "success": True,
                "data": [],
                "meta": {"total_resources": 0, "showing": 0},
                "warning": "OCI Usage API is rate-limited (429). Retry shortly.",
            }
        raise HTTPException(status_code=500, detail=str(e))

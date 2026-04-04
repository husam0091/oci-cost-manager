"""Dashboard endpoints with locked decision-first summary contract."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from api.schemas.dashboard import (
    BudgetHealthModel,
    CoreBusinessSpotlightItemModel,
    DashboardSummaryData,
    ExecutiveSignalsModel,
    DashboardSummaryResponse,
    FreshnessModel,
    LicenseItemModel,
    LicenseSpotlightModel,
    MappingHealthModel,
    HighestBudgetUtilizationModel,
    MoverModel,
    PeriodModel,
    StorageBackupModel,
    StorageItemModel,
    SpotlightServiceModel,
    SpotlightTotalsModel,
    SavingsOpportunitiesModel,
    TopDriverModel,
    TotalsModel,
)
from core.database import get_db
from core.cache import get_cached, set_cached
from core.models import Compartment, CostSnapshot, Resource, ScanRun, Setting
from services import get_cost_calculator
from services.budget_engine import evaluate_budget_statuses
from services.recommendations import generate_recommendations
from api.utils.dates import compute_previous_period, iso_date, parse_iso_datetime

router = APIRouter()
SUMMARY_CACHE_TTL = 90


def _to_iso_date(dt: datetime) -> str:
    return dt.astimezone(UTC).date().isoformat()


def _to_iso_utc(dt: Optional[datetime]) -> Optional[str]:
    if not dt:
        return None
    return dt.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _cache_key(start_date: str, end_date: str, compare: str, region: Optional[str] = None) -> str:
    base = f"dashboard_summary|start={start_date}|end={end_date}|compare={compare}"
    if region and region != "all":
        base += f"|region={region}"
    return base


def _get_allowed_resource_ids(db: Session, region: Optional[str]):
    """Return set of resource OCIDs for the given region, or None for no filter."""
    if not region or region == "all":
        return None
    rows = db.query(Resource.ocid).filter(Resource.region == region).all()
    return {r.ocid for r in rows if r.ocid}


def _safe_pct(delta: float, base: float) -> float:
    if base == 0:
        return 0.0
    return (delta / base) * 100.0


def _classify_resource(resource: Optional[Resource], sku_names: str) -> tuple[str, str, str]:
    text = sku_names.lower()
    rtype = (resource.type or "").lower() if resource else ""
    details = resource.details or {} if resource else {}
    image_name = str(details.get("image_name") or "").lower()
    image_vendor = str(details.get("image_vendor") or "").lower()
    name = (resource.name or "").lower() if resource else ""

    if rtype == "sql_server" or "sql server" in text or "microsoft sql" in text:
        return "sql_server", "high", "resource_type_or_sku"
    if "windows os" in text or "windows" in image_name or rtype == "windows_server":
        conf = "high" if "windows" in image_name or rtype == "windows_server" else "medium"
        reason = "image_name_or_type" if conf == "high" else "sku_hint"
        return "windows", conf, reason
    if "oracle linux" in text or "oracle os" in text or "oracle linux" in image_name:
        conf = "high" if "oracle linux" in image_name else "medium"
        reason = "image_name" if conf == "high" else "sku_hint"
        return "oracle_os", conf, reason

    # Security appliance detection intentionally conservative to avoid fake counts.
    if "fortigate" in image_name or "fortinet" in image_vendor:
        return "security_forti", "high", "image_vendor_or_name"
    if "fortigate" in text:
        return "security_forti", "low", "sku_hint_only"
    if "palo alto" in image_name or "paloalto" in image_name:
        return "security_palo", "high", "image_name"
    if "palo alto" in text:
        return "security_palo", "low", "sku_hint_only"
    if "f5" in image_name and "sql" not in image_name:
        return "security_f5", "high", "image_name"
    if "f5" in text:
        return "security_f5", "low", "sku_hint_only"

    if rtype in {"block_volume", "boot_volume"} and str(details.get("attachment_state") or "").upper() == "UNATTACHED":
        return "unattached_volume", "high", "resource_attachment_state"
    if "backup" in text or "snapshot" in text:
        return "backup", "medium", "sku_hint"
    if "unattached" in name:
        return "unattached_volume", "medium", "name_hint"
    return "unclassified", "low", "no_reliable_match"


def _descendants(selected_ids: set[str], compartments: list[Compartment]) -> set[str]:
    children: dict[str, list[str]] = {}
    for comp in compartments:
        if comp.parent_id:
            children.setdefault(comp.parent_id, []).append(comp.id)
    out = set(selected_ids)
    stack = list(selected_ids)
    while stack:
        parent = stack.pop()
        for child in children.get(parent, []):
            if child not in out:
                out.add(child)
                stack.append(child)
    return out


def _guess_service_from_skus(skus: list[dict]) -> str:
    text = " ".join((s.get("sku_name") or "") for s in skus).lower()
    if "sql" in text or "database" in text:
        return "Database"
    if "block volume" in text or "boot volume" in text or "object storage" in text or "backup" in text or "snapshot" in text:
        return "Storage"
    if "network" in text or "load balancer" in text:
        return "Network"
    return "Compute"


@router.get("/summary", response_model=DashboardSummaryResponse)
async def dashboard_summary(
    start_date: str = Query(..., description="ISO date/datetime start"),
    end_date: str = Query(..., description="ISO date/datetime end (inclusive)"),
    compare: str = Query("previous"),
    region: Optional[str] = Query(None, description="Filter to a specific OCI region (omit or 'all' for all regions)"),
    db: Session = Depends(get_db),
):
    """Locked contract summary endpoint for decision-first dashboard."""
    if compare != "previous":
        raise HTTPException(status_code=422, detail="compare must be 'previous'")

    start = parse_iso_datetime(start_date, is_end=False, required=True)
    end_exclusive = parse_iso_datetime(end_date, is_end=True, required=True)
    normalized_start = iso_date(start)
    normalized_end = iso_date(end_exclusive - timedelta(days=1))
    region_filter = region if (region and region != "all") else None
    cached = get_cached(_cache_key(normalized_start, normalized_end, compare, region=region))
    if cached is not None:
        return DashboardSummaryResponse(**cached)
    if end_exclusive <= start:
        raise HTTPException(status_code=422, detail="end_date must be on/after start_date")

    period_days = (end_exclusive - start).days
    prev_start, prev_end = compute_previous_period(start, end_exclusive)

    calc = get_cost_calculator()

    def _fetch_all():
        return (
            calc.get_costs_by_service(start, end_exclusive, region=region_filter),
            calc.get_costs_by_service(prev_start, prev_end, region=region_filter),
            calc.get_costs_by_resource(start, end_exclusive, include_skus=True, region=region_filter),
            calc.get_costs_by_resource(prev_start, prev_end, region=region_filter),
        )

    try:
        loop = asyncio.get_event_loop()
        current_by_service, previous_by_service, current_resources, previous_resources = await asyncio.wait_for(
            loop.run_in_executor(None, _fetch_all),
            timeout=70.0,
        )
    except asyncio.TimeoutError:
        raise HTTPException(status_code=503, detail="OCI Usage API timed out — please retry shortly")
    except Exception as exc:
        err_str = str(exc)
        if "429" in err_str or "TooManyRequests" in err_str:
            raise HTTPException(status_code=503, detail="OCI Usage API rate-limited — please retry shortly")
        raise HTTPException(status_code=503, detail=f"OCI Usage API unavailable: {type(exc).__name__}")
    current_total = float(sum(current_by_service.values()))
    previous_total = float(sum(previous_by_service.values()))
    total_delta = current_total - previous_total

    services = set(current_by_service.keys()) | set(previous_by_service.keys())
    service_rows = []
    for service in services:
        cur = float(current_by_service.get(service, 0.0))
        prv = float(previous_by_service.get(service, 0.0))
        delta = cur - prv
        service_rows.append(
            {
                "service": service,
                "current": cur,
                "previous": prv,
                "delta_abs": delta,
                "delta_pct": _safe_pct(delta, prv),
                "share_pct": (cur / current_total * 100.0) if current_total else 0.0,
            }
        )
    service_rows.sort(key=lambda r: r["current"], reverse=True)

    if service_rows:
        td = service_rows[0]
        top_driver = TopDriverModel(
            group=td["service"],
            current=round(td["current"], 2),
            previous=round(td["previous"], 2),
            share_pct=round(td["share_pct"], 2),
            delta_abs=round(td["delta_abs"], 2),
            delta_pct=round(td["delta_pct"], 2),
        )
        bm = max(service_rows, key=lambda r: abs(r["delta_abs"]))
        biggest_mover = MoverModel(
            entity_type="service",
            entity_name=bm["service"],
            delta_abs=round(bm["delta_abs"], 2),
            delta_pct=round(bm["delta_pct"], 2),
        )
    else:
        top_driver = TopDriverModel(group="No data", current=0.0, previous=0.0, share_pct=0.0, delta_abs=0.0, delta_pct=0.0)
        biggest_mover = MoverModel(entity_type="service", entity_name="No data", delta_abs=0.0, delta_pct=0.0)

    previous_by_resource = {r.get("resource_id"): float(r.get("total_cost") or 0.0) for r in previous_resources}

    resource_ids = [r.get("resource_id") for r in current_resources if r.get("resource_id")]
    resources = db.query(Resource).filter(Resource.ocid.in_(resource_ids)).all() if resource_ids else []
    resources_by_ocid = {r.ocid: r for r in resources}

    windows_cur = windows_prev = 0.0
    sql_cur = sql_prev = 0.0
    oracle_cur = oracle_prev = 0.0
    unattached_count = 0
    unattached_monthly = 0.0
    backups_count = 0
    backups_monthly = 0.0
    unallocated_count = 0
    low_confidence_count = 0

    for row in current_resources:
        rid = row.get("resource_id")
        cur = float(row.get("total_cost") or 0.0)
        prv = float(previous_by_resource.get(rid, 0.0))
        skus = row.get("skus") or []
        sku_text = " ".join((sku.get("sku_name") or "") for sku in skus)
        resource = resources_by_ocid.get(rid)
        category, match_confidence, match_reason = _classify_resource(resource, sku_text)

        # Internal trust model (kept server-side even when not exposed in response model yet).
        _ = {"match_confidence": match_confidence, "match_reason": match_reason}

        if category == "windows":
            windows_cur += cur
            windows_prev += prv
        elif category == "sql_server":
            sql_cur += cur
            sql_prev += prv
        elif category == "oracle_os":
            oracle_cur += cur
            oracle_prev += prv
        elif category == "unattached_volume":
            unattached_count += 1
            unattached_monthly += cur

        if any("backup" in (s.get("sku_name") or "").lower() or "snapshot" in (s.get("sku_name") or "").lower() for s in skus):
            backups_monthly += sum(float(s.get("cost") or 0.0) for s in skus if "backup" in (s.get("sku_name") or "").lower() or "snapshot" in (s.get("sku_name") or "").lower())
            qty_sum = sum(float(s.get("quantity") or 0.0) for s in skus if "backup" in (s.get("sku_name") or "").lower() or "snapshot" in (s.get("sku_name") or "").lower())
            backups_count += int(round(qty_sum)) if qty_sum > 0 else 1

        if category == "unclassified":
            unallocated_count += 1
        if match_confidence == "low":
            low_confidence_count += 1

    resource_count = len(current_resources)
    unallocated_pct = (unallocated_count / resource_count * 100.0) if resource_count else 0.0

    latest_scan = db.query(ScanRun).order_by(ScanRun.started_at.desc()).first()
    latest_cost = db.query(CostSnapshot).order_by(CostSnapshot.end_date.desc()).first()

    try:
        settings = db.query(Setting).filter(Setting.id == 1).one_or_none()
        all_compartments = db.query(Compartment).all()
    except SQLAlchemyError:
        # Backward-compatible fallback for partially migrated local DBs.
        settings = None
        all_compartments = []
    selected_compartments = list(
        (settings.important_compartments if settings and settings.important_compartments is not None else None)
        or (settings.important_compartment_ids if settings else None)
        or []
    )
    if not selected_compartments:
        selected_compartments = [c.id for c in all_compartments if c.name and c.name.lower() in {"foo", "ad1"}]
    include_children = bool(settings.important_include_children) if settings else True
    compartment_name_map = {c.id: c.name for c in all_compartments}
    prev_resources_by_id = {r.get("resource_id"): r for r in previous_resources}
    core_business_spotlight: list[CoreBusinessSpotlightItemModel] = []

    for cid in selected_compartments:
        scope = _descendants({cid}, all_compartments) if include_children else {cid}
        current_in_scope = []
        previous_in_scope = []
        for row in current_resources:
            resource = resources_by_ocid.get(row.get("resource_id"))
            comp_id = resource.compartment_id if resource else row.get("compartment_id")
            if comp_id in scope:
                current_in_scope.append(row)
                prev_row = prev_resources_by_id.get(row.get("resource_id"))
                if prev_row:
                    previous_in_scope.append(prev_row)

        current_scope_total = float(sum(float(r.get("total_cost") or 0.0) for r in current_in_scope))
        previous_scope_total = float(sum(float(r.get("total_cost") or 0.0) for r in previous_in_scope))
        scope_delta = current_scope_total - previous_scope_total

        service_cur: dict[str, float] = {}
        service_prev: dict[str, float] = {}
        for row in current_in_scope:
            svc = _guess_service_from_skus(row.get("skus") or [])
            service_cur[svc] = service_cur.get(svc, 0.0) + float(row.get("total_cost") or 0.0)
        for row in previous_in_scope:
            svc = _guess_service_from_skus(row.get("skus") or [])
            service_prev[svc] = service_prev.get(svc, 0.0) + float(row.get("total_cost") or 0.0)

        svc_rows = []
        svc_names = set(service_cur.keys()) | set(service_prev.keys())
        for name in svc_names:
            cur = float(service_cur.get(name, 0.0))
            prev = float(service_prev.get(name, 0.0))
            delta = cur - prev
            svc_rows.append(
                {
                    "name": name,
                    "current": cur,
                    "previous": prev,
                    "delta_abs": delta,
                    "delta_pct": _safe_pct(delta, prev),
                    "share_pct": (cur / current_scope_total * 100.0) if current_scope_total else 0.0,
                }
            )
        svc_rows.sort(key=lambda r: r["current"], reverse=True)
        top_services = svc_rows[:3]
        if len(svc_rows) > 3:
            rem = svc_rows[3:]
            rem_cur = sum(r["current"] for r in rem)
            rem_prev = sum(r["previous"] for r in rem)
            rem_delta = rem_cur - rem_prev
            top_services.append(
                {
                    "name": "Other",
                    "current": rem_cur,
                    "delta_abs": rem_delta,
                    "delta_pct": _safe_pct(rem_delta, rem_prev),
                    "share_pct": (rem_cur / current_scope_total * 100.0) if current_scope_total else 0.0,
                }
            )
        spotlight_services = [
            SpotlightServiceModel(
                name=r["name"],
                current=round(r["current"], 2),
                share_pct=round(r["share_pct"], 2),
                delta_abs=round(r["delta_abs"], 2),
                delta_pct=round(r["delta_pct"], 2),
            )
            for r in top_services
        ]
        core_business_spotlight.append(
            CoreBusinessSpotlightItemModel(
                compartment_id=cid,
                compartment_name=compartment_name_map.get(cid, cid),
                include_children=include_children,
                totals=SpotlightTotalsModel(
                    current=round(current_scope_total, 2),
                    previous=round(previous_scope_total, 2),
                    delta_abs=round(scope_delta, 2),
                    delta_pct=round(_safe_pct(scope_delta, previous_scope_total), 2),
                ),
                top_services=spotlight_services,
            )
        )

    data = DashboardSummaryData(
        period=PeriodModel(
            start_date=_to_iso_date(start),
            end_date=_to_iso_date(end_exclusive - timedelta(days=1)),
            days=period_days,
        ),
        totals=TotalsModel(
            current=round(current_total, 2),
            previous=round(previous_total, 2),
            delta_abs=round(total_delta, 2),
            delta_pct=round(_safe_pct(total_delta, previous_total), 2),
        ),
        top_driver=top_driver,
        biggest_mover=biggest_mover,
        license_spotlight=LicenseSpotlightModel(
            windows=LicenseItemModel(
                monthly_cost=round(windows_cur, 2),
                daily_estimate=round(windows_cur / period_days, 2) if period_days else 0.0,
                delta_abs=round(windows_cur - windows_prev, 2),
            ),
            sql_server=LicenseItemModel(
                monthly_cost=round(sql_cur, 2),
                daily_estimate=round(sql_cur / period_days, 2) if period_days else 0.0,
                delta_abs=round(sql_cur - sql_prev, 2),
            ),
            oracle_os=LicenseItemModel(
                monthly_cost=round(oracle_cur, 2),
                daily_estimate=round(oracle_cur / period_days, 2) if period_days else 0.0,
                delta_abs=round(oracle_cur - oracle_prev, 2),
            ),
        ),
        storage_backup=StorageBackupModel(
            unattached_volumes=StorageItemModel(
                count=unattached_count,
                monthly_cost=round(unattached_monthly, 2),
            ),
            backups=StorageItemModel(
                count=backups_count,
                monthly_cost=round(backups_monthly, 2),
            ),
        ),
        mapping_health=MappingHealthModel(
            unallocated_pct=round(unallocated_pct, 2),
            low_confidence_count=low_confidence_count,
        ),
        freshness=FreshnessModel(
            last_scan_at=_to_iso_utc(latest_scan.finished_at if latest_scan else None),
            last_cost_refresh_at=_to_iso_utc(latest_cost.end_date if latest_cost else None),
        ),
        core_business_spotlight=core_business_spotlight,
        savings_opportunities=SavingsOpportunitiesModel(
            potential_savings_monthly=0.0,
            high_confidence_savings=0.0,
            recommendation_count=0,
        ),
        budget_health=BudgetHealthModel(
            total_budgets=0,
            budgets_at_risk=0,
            budgets_breached=0,
            highest_utilization_budget=None,
        ),
        executive_signals=ExecutiveSignalsModel(
            run_rate_vs_budget="No budget data available.",
            forecasted_month_end_spend="No forecast data available.",
            top_risk_budget="No risk budget identified.",
            top_cost_driver_this_month="No cost driver identified.",
        ),
    )
    rec_payload = generate_recommendations(db=db, start=start, end_exclusive=end_exclusive)
    rec_items = rec_payload["items"]
    data.savings_opportunities = SavingsOpportunitiesModel(
        potential_savings_monthly=round(sum(i.estimated_savings for i in rec_items), 2),
        high_confidence_savings=round(sum(i.estimated_savings for i in rec_items if i.confidence == "high"), 2),
        recommendation_count=len(rec_items),
    )
    budget_statuses = evaluate_budget_statuses(db, persist_alerts=True)
    highest = max(budget_statuses, key=lambda x: x.utilization_pct) if budget_statuses else None
    data.budget_health = BudgetHealthModel(
        total_budgets=len(budget_statuses),
        budgets_at_risk=sum(1 for x in budget_statuses if x.breach_level == "warning"),
        budgets_breached=sum(1 for x in budget_statuses if x.breach_level == "critical"),
        highest_utilization_budget=(
            HighestBudgetUtilizationModel(
                budget_id=highest.budget_id,
                budget_name=highest.budget_name,
                utilization_pct=round(highest.utilization_pct, 2),
            )
            if highest
            else None
        ),
    )
    total_budget_limit = sum(x.budget_limit for x in budget_statuses)
    total_budget_spend = sum(x.current_spend for x in budget_statuses)
    total_budget_forecast = sum(x.forecast_end_of_month for x in budget_statuses)
    top_risk = next((item for item in sorted(budget_statuses, key=lambda b: b.utilization_pct, reverse=True) if item.breach_level in {"warning", "critical"}), None)
    top_driver_sentence = f"Top driver this month is {top_driver.group} at {top_driver.share_pct:.2f}% share."
    if not top_driver.group or top_driver.group == "No data":
        top_driver_sentence = "No cost driver identified."
    data.executive_signals = ExecutiveSignalsModel(
        run_rate_vs_budget=(
            f"Run-rate is {(_safe_pct(total_budget_spend, total_budget_limit) if total_budget_limit else 0.0):.2f}% of configured budgets."
            if total_budget_limit
            else "No budget data available."
        ),
        forecasted_month_end_spend=(
            f"Forecasted month-end spend across budgets is ${total_budget_forecast:,.2f}."
            if budget_statuses
            else "No forecast data available."
        ),
        top_risk_budget=(
            f"Top risk budget is {top_risk.budget_name} at {top_risk.utilization_pct:.2f}% utilization."
            if top_risk
            else "No risk budget identified."
        ),
        top_cost_driver_this_month=top_driver_sentence,
    )
    response = DashboardSummaryResponse(success=True, data=data)
    set_cached(_cache_key(normalized_start, normalized_end, compare, region=region), response.model_dump(), SUMMARY_CACHE_TTL)
    return response

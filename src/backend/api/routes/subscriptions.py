"""Subscriptions endpoint – Universal Credits committed vs consumed."""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Optional
from fastapi import APIRouter

from services.cost_calculator import get_cost_calculator
from core.cache import get_cached, set_cached

router = APIRouter()

_CACHE_TTL = 900  # 15-minute cache for cost data


@router.get("")
async def get_subscriptions():
    """Return Universal Credit consumption data from the OCI Usage API.

    Consumed YTD/MTD = OCI Usage API computed_amount (same as Cost Analysis).
    Committed amount = not available without manage onesubscription in tenancy;
    set manually in the Dashboard UI instead.
    """
    cache_key = f"subscriptions_v3_{datetime.now(UTC).strftime('%Y-%m-%d_%H')}"
    cached = get_cached(cache_key)
    if cached is not None:
        return {"success": True, "data": cached, "cached": True}

    # ── Subscription API not attempted (unreachable in most deployments) ───
    subscriptions: list = []
    subscription_error: Optional[str] = None

    # ── 2. YTD consumed cost from Usage API ────────────────────────────────
    today = datetime.now(UTC)
    year_start = today.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    mtd_start = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    total_consumed_ytd: Optional[float] = None
    total_consumed_mtd: Optional[float] = None
    try:
        calc = get_cost_calculator()
        ytd_costs = calc.get_costs_by_service(year_start, today)
        total_consumed_ytd = round(sum(ytd_costs.values()), 2)
        mtd_costs = calc.get_costs_by_service(mtd_start, today)
        total_consumed_mtd = round(sum(mtd_costs.values()), 2)
    except Exception:
        pass

    # ── 3. Aggregate committed from active subscriptions ───────────────────
    active_statuses = {"active", "subscribed", "signed", ""}
    total_committed = sum(
        s["total_value"]
        for s in subscriptions
        if (s.get("status") or "").lower() in active_statuses
    )
    total_committed = round(total_committed, 2)

    remaining: Optional[float] = None
    utilization_pct: Optional[float] = None
    if total_committed > 0 and total_consumed_ytd is not None:
        remaining = round(total_committed - total_consumed_ytd, 2)
        utilization_pct = round(min(total_consumed_ytd / total_committed * 100, 100), 2)

    result = {
        "subscriptions": subscriptions,
        "total_committed": total_committed,
        "total_consumed_ytd": total_consumed_ytd,
        "total_consumed_mtd": total_consumed_mtd,
        "remaining": remaining,
        "utilization_pct": utilization_pct,
        "year_start": year_start.date().isoformat(),
        "as_of": today.date().isoformat(),
        "subscription_api_available": len(subscriptions) > 0,
        "subscription_error": subscription_error,
    }

    set_cached(cache_key, result, _CACHE_TTL)
    return {"success": True, "data": result, "cached": False}

"""Legacy subscription summary, backed by the same contracts as Commitments."""

from datetime import UTC, datetime
from typing import Optional
from fastapi import APIRouter, Cookie, Depends
from sqlalchemy.orm import Session
from core.database import get_db
from core.models import SubscriptionContract
from api.routes.commitments import authorize, contract_json
from services.cost_calculator import get_cost_calculator
from services.commitments import D, spend_eligible
from core.cache import get_cached, set_cached

router = APIRouter()


@router.get("")
def get_subscriptions(
    token: Optional[str] = Cookie(None, alias="access_token"),
    db: Session = Depends(get_db),
):
    principal = authorize(db, token)
    now = datetime.now(UTC)
    rows = (
        db.query(SubscriptionContract)
        .filter(
            SubscriptionContract.start_date <= now.date(),
            SubscriptionContract.end_date > now.date(),
        )
        .all()
    )
    rows = [
        row
        for row in rows
        if spend_eligible(row)
        and row.status.lower()
        not in {"expired", "cancelled", "canceled", "terminated", "inactive"}
    ]
    key = f"subscriptions_terms_v5_{principal.username}_{now:%Y-%m-%d_%H}_{max((str(r.computed_at) for r in rows), default='empty')}"
    cached = get_cached(key)
    if cached is not None:
        return {"success": True, "data": cached, "cached": True}
    year_start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    totals, error = {}, None
    try:
        calc = get_cost_calculator()
        for label, start in (("ytd", year_start), ("mtd", month_start)):
            for item in calc.get_usage_summary(start, now, group_by=["service"]):
                currency = str(item.get("currency") or "").strip()
                if not currency and not D(item["computed_amount"]):
                    continue
                values = totals.setdefault(
                    currency or "Unspecified",
                    {"currency": currency or "Unspecified", "ytd": D(0), "mtd": D(0)},
                )
                values[label] += D(item["computed_amount"])
    except Exception:
        error = "Usage unavailable; see billing diagnostics"
        totals = {}
    # Multiple overlapping contracts cannot be added automatically, even in the same currency.
    monetary = [
        row for row in rows if row.total_value is not None and row.total_value > 0
    ]
    single = monetary[0] if len(monetary) == 1 else None
    currency = (
        single.currency
        if single
        else (next(iter(totals)) if len(totals) == 1 else None)
    )
    consumed = totals.get(currency) if currency else None
    result = {
        "subscriptions": [contract_json(row) for row in rows],
        "total_committed": (
            float(single.total_value)
            if single and single.total_value is not None
            else None
        ),
        "total_consumed_ytd": float(consumed["ytd"]) if consumed else None,
        "total_consumed_mtd": float(consumed["mtd"]) if consumed else None,
        "currency": currency,
        "remaining": None,
        "utilization_pct": None,
        "year_start": year_start.date().isoformat(),
        "as_of": now.date().isoformat(),
        "subscription_api_available": any(
            row.source.startswith("oci:") for row in rows
        ),
        "subscription_error": error,
        "totals_by_currency": [
            {k: float(v) if k != "currency" else v for k, v in value.items()}
            for value in totals.values()
        ],
        "note": "Use Commitments for term-based comparisons. YTD is not subscription term consumption; overlapping contracts are not added.",
    }
    set_cached(key, result, 600)
    return {"success": True, "data": result, "cached": False}

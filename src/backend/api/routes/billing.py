"""Authenticated, auditable drill-down of actual OCI Usage API charges."""

import asyncio
import hashlib
import json
from datetime import UTC, datetime
from typing import Optional

from fastapi import APIRouter, Cookie, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from api.utils.dates import parse_required_range
from core.cache import get_cached, set_cached
from core.database import get_db
from core.models import Resource
from core.rbac import resolve_principal
from services import get_cost_calculator
from services.allocation import evaluate_allocation, load_enabled_rules
from services.spend_explorer import explain_spend

router = APIRouter()


@router.get("/spend")
async def spend(
    start_date: str = Query(...),
    end_date: str = Query(...),
    region: Optional[str] = Query(None),
    service: Optional[str] = Query(None),
    resource_id: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    refresh: bool = Query(False),
    token: Optional[str] = Cookie(default=None, alias="access_token"),
    db: Session = Depends(get_db),
):
    start, end, days = parse_required_range(start_date, end_date)
    if days > 366:
        raise HTTPException(
            status_code=422, detail="Choose a range of at most 366 days"
        )
    try:
        principal = resolve_principal(db, token, strict=True)
    except PermissionError:
        raise HTTPException(status_code=401, detail="Sign in to view billed spend")
    scope = [
        principal.username,
        principal.role,
        sorted(principal.allowed_teams),
        sorted(principal.allowed_apps),
        sorted(principal.allowed_envs),
        sorted(principal.allowed_compartment_ids),
    ]
    key = (
        "billing_spend_v2_"
        + hashlib.sha256(
            json.dumps(
                [
                    scope,
                    start.isoformat(),
                    end.isoformat(),
                    region,
                    service,
                    resource_id,
                ]
            ).encode()
        ).hexdigest()
    )
    result = None if refresh else get_cached(key)
    cached = result is not None
    if result is None:
        # Keep within OCI's four grouping dimensions, including currency.
        # Resource drill-down adds unit and part number for an effective billed rate.
        grouping = (
            ["skuName", "skuPartNumber", "unit"]
            if resource_id
            else ["service", "skuName", "resourceId"]
        )
        try:
            calculator = get_cost_calculator()
            items = await asyncio.to_thread(
                calculator.get_usage_summary,
                start_date=start,
                end_date=end,
                granularity="MONTHLY",
                group_by=grouping,
                region=region,
                service=service,
                resource_id=resource_id,
            )
        except Exception:
            raise HTTPException(
                status_code=503,
                detail="OCI billing is unavailable. Check Diagnostics and retry; no estimated data was substituted.",
            )
        # Names/region are inventory enrichment, not inferred billing dimensions.
        resource_map = {r.ocid: r for r in db.query(Resource).all()}
        restricted = not principal.is_admin and any(
            (
                principal.allowed_teams,
                principal.allowed_apps,
                principal.allowed_envs,
                principal.allowed_compartment_ids,
            )
        )
        if restricted:
            rules = load_enabled_rules(db)
            visible = []
            for item in items:
                model = resource_map.get(item.get("resource_id") or resource_id)
                if model is None:
                    continue  # Cannot prove scope for unattributed/unscanned resources.
                allocation = evaluate_allocation(model, rules)
                dimensions = [
                    (principal.allowed_teams, allocation.team),
                    (principal.allowed_apps, allocation.app),
                    (principal.allowed_envs, allocation.env),
                    (principal.allowed_compartment_ids, model.compartment_id),
                ]
                if all(
                    not allowed or value in allowed for allowed, value in dimensions
                ):
                    visible.append(item)
            items = visible
        result = explain_spend(
            items, resource_map, service=service, resource_id=resource_id
        )
        result["generated_at"] = datetime.now(UTC).isoformat()
        result["scope_limited"] = restricted
        set_cached(key, result, 600)
    count = len(result["items"])
    return {
        "success": True,
        "data": {**result, "items": result["items"][offset : offset + limit]},
        "meta": {
            "source": "OCI Usage API",
            "basis": "OCI-reported computedAmount; not a list-price estimate",
            "cached": cached,
            "cache_ttl_seconds": 600,
            "start_date": start.isoformat(),
            "end_date_exclusive": end.isoformat(),
            "total": count,
            "returned": len(result["items"][offset : offset + limit]),
            "offset": offset,
            "limit": limit,
            "has_more": offset + limit < count,
            "notes": [
                "Recent usage may be delayed. This is not a final invoice; taxes, fees and invoice adjustments may differ.",
                "Currencies are kept separate. Negative amounts remain credits/adjustments.",
                "Resource names and regions are enriched from inventory and may be unavailable for deleted resources.",
                "Choose a resource to retrieve quantity, unit and effective billed rate. Rate is cost divided by usage, not the public list price.",
                "PAYG describes a commercial billing plan; License Included and BYOL describe software licensing. Confirm subscription and entitlement terms separately.",
            ],
        },
    }

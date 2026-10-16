"""DB-backed commitment views; SDK work only occurs in the heavy queue."""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
import hashlib
import json
import uuid
from typing import Literal, Optional
from fastapi import APIRouter, Cookie, Depends, HTTPException, Query
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import case
from sqlalchemy.orm import Session
from core.cache import get_cached, set_cached
from core.database import get_db
from core.models import (
    SubscriptionContract,
    SubscriptionPeriod,
    SubscriptionSyncRun,
    Setting,
    Compartment,
)
from core.rbac import resolve_principal
from services.commitments import D, queue_sync, month_at, category, spend_eligible
from services.subscription_sources import POLICIES
from services.subscription_terms import visible, group_label
from core.models import SubscriptionContractLine

router = APIRouter()


def authorize(db, token, write=False):
    try:
        principal = resolve_principal(db, token, strict=True)
    except PermissionError:
        raise HTTPException(401, "Sign in to view commitments")
    setting = db.get(Setting, 1)
    if setting and not setting.commitments_enabled:
        raise HTTPException(404, "Commitments is disabled")
    # A tenancy contract's allowance cannot safely be inferred for scoped teams.
    if not principal.is_admin and any(
        (
            principal.allowed_teams,
            principal.allowed_apps,
            principal.allowed_envs,
            principal.allowed_compartment_ids,
        )
    ):
        raise HTTPException(
            403,
            "Commitments requires tenancy-wide scope. Team allowances have not been assigned; use the scoped Spend explorer.",
        )
    if write and principal.role not in {"admin", "finops"}:
        raise HTTPException(403, "Administrator or FinOps role required")
    return principal


def contract_json(row):
    return {
        "id": row.id,
        "source": row.source,
        "name": row.name,
        "status": row.status,
        "start_date": row.start_date.isoformat(),
        "end_date_exclusive": row.end_date.isoformat(),
        "total_value": float(row.total_value) if row.total_value is not None else None,
        "currency": row.currency,
        "term_months": row.term_months,
        "computed_at": row.computed_at.isoformat(),
        "manual": row.source == "manual",
        "selector_group": group_label(row),
        "source_label": (
            "Entered manually" if row.source == "manual" else "From OCI subscription"
        ),
        "line_count": len((row.details or {}).get("source_line_ids", [])),
        "grouping_note": (row.details or {}).get("grouping_note"),
        "payment_model": (row.details or {}).get("payment_model"),
        "spend_category": (
            "oci_infrastructure"
            if row.source == "manual"
            else category((row.details or {}).get("source_evidence") or {})
        ),
        "resource_usage_applicable": spend_eligible(row),
        "parent_subscription_id": (row.details or {}).get("parent_subscription_id"),
        "classic_subscription_id": (row.details or {}).get("classic_subscription_id"),
        "subscribed_service_id": (row.details or {}).get("subscribed_service_id"),
    }


def diagnostics(db):
    run = (
        db.query(SubscriptionSyncRun)
        .order_by(SubscriptionSyncRun.started_at.desc())
        .first()
    )
    return {
        "sync_run_id": run.id if run else None,
        "status": run.status if run else "not_synced",
        "computed_at": run.finished_at.isoformat() if run and run.finished_at else None,
        "sources": (
            {
                key: {
                    **value,
                    **({"error": value["error"][:700]} if "error" in value else {}),
                }
                for key, value in list((run.sources or {}).items())[:100]
            }
            if run
            else {}
        ),
        "policies": POLICIES,
        "iam_note": "401/403/404 can indicate permission, tenancy, region or entitlement issues. Organizations and Usage policies are documented below. OneSubscription/OSP entitlement policies must be confirmed with Oracle for this account; no unverified policy is suggested.",
    }


@router.get("/contracts")
def contracts(
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    token: Optional[str] = Cookie(None, alias="access_token"),
    db: Session = Depends(get_db),
):
    authorize(db, token)
    rows = db.query(SubscriptionContract).order_by(
        case((SubscriptionContract.total_value.is_(None), 1), else_=0),
        case((SubscriptionContract.source == "manual", 1), else_=0),
        SubscriptionContract.start_date.desc(),
    )
    selected = [row for row in rows.all() if visible(row)]
    return {
        "success": True,
        "data": [contract_json(row) for row in selected[offset : offset + limit]],
        "meta": {
            "total": len(selected),
            "diagnostics": diagnostics(db),
            "estimates": ["manual_contracts"],
        },
    }


class ManualContract(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    total_value: Decimal = Field(gt=0, max_digits=24, decimal_places=8)
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    start_date: date
    end_date: date
    term_months: int = Field(ge=1, le=120)
    oci_subscription_id: Optional[str] = Field(default=None, max_length=255)

    @model_validator(mode="after")
    def valid_term(self):
        if (
            not self.start_date
            < self.end_date
            <= month_at(self.start_date, self.term_months)
        ):
            raise ValueError(
                "End is exclusive, after start and no later than term months"
            )
        if self.end_date <= month_at(self.start_date, self.term_months - 1):
            raise ValueError(
                "Term months must include only the actual contract windows"
            )
        return self


@router.post("/contracts", status_code=201)
def manual(
    body: ManualContract,
    token: Optional[str] = Cookie(None, alias="access_token"),
    db: Session = Depends(get_db),
):
    principal = authorize(db, token, write=True)
    values = body.model_dump(exclude={"oci_subscription_id"})
    row = SubscriptionContract(
        id=str(uuid.uuid4()),
        source="manual",
        status="active",
        computed_at=datetime.now(UTC),
        details={
            "created_by": principal.username,
            "estimate": True,
            "oci_subscription_id": body.oci_subscription_id,
        },
        **values,
    )
    db.add(row)
    db.commit()
    return {
        "success": True,
        "data": contract_json(row),
        "meta": {"source": "manual", "sync_required": True},
    }


@router.post("/sync", status_code=202)
def trigger(
    token: Optional[str] = Cookie(None, alias="access_token"),
    db: Session = Depends(get_db),
):
    authorize(db, token, write=True)
    try:
        job_id = queue_sync(db)
    except Exception:
        raise HTTPException(
            503, "Subscription sync could not be queued; check worker connectivity"
        )
    return {"success": True, "data": {"job_id": job_id, "status": "queued"}}


@router.get("/diagnostics")
def source_diagnostics(
    token: Optional[str] = Cookie(None, alias="access_token"),
    db: Session = Depends(get_db),
):
    authorize(db, token)
    return {"success": True, "data": diagnostics(db)}


def period_json(row, currency, region):
    facts = (row.details or {}).get("facts", [])
    selected = [
        r
        for r in facts
        if r["currency"] == currency
        and (not region or region == "all" or r["region"] == region)
    ]
    complete = (row.details or {}).get("complete", False)
    charges = (
        sum((D(r["amount"]) for r in selected if D(r["amount"]) >= 0), Decimal(0))
        if complete
        else None
    )
    credits = (
        sum((D(r["amount"]) for r in selected if D(r["amount"]) < 0), Decimal(0))
        if complete
        else None
    )
    actual = charges + credits if complete else None
    elapsed = (row.details or {}).get("elapsed_days", 1)
    forecast = (
        actual * D((row.end_date - row.start_date).days) / D(elapsed)
        if actual is not None
        else None
    )
    return {
        "id": row.id,
        "start_date": row.start_date.isoformat(),
        "end_date_exclusive": row.end_date.isoformat(),
        "allowance": float(row.allowance) if row.allowance is not None else None,
        "actual": float(actual) if actual is not None else None,
        "charges": float(charges) if charges is not None else None,
        "credits": float(credits) if credits is not None else None,
        "forecast": float(forecast) if forecast is not None else None,
        "computed_at": row.computed_at.isoformat(),
        "complete": complete,
        "elapsed_days": elapsed,
    }


def view(db, contract_id, mode, region, principal):
    if contract_id:
        contract = db.get(SubscriptionContract, contract_id)
        if contract and (contract.details or {}).get("superseded_by"):
            contract = db.get(SubscriptionContract, contract.details["superseded_by"])
        if contract and not visible(contract):
            contract = None
    else:
        candidates = (
            db.query(SubscriptionContract)
            .filter(
                SubscriptionContract.start_date <= date.today(),
                SubscriptionContract.end_date > date.today(),
            )
            .all()
        )
        candidates = [
            row
            for row in candidates
            if visible(row)
            and spend_eligible(row)
            and row.total_value is not None
            and row.total_value > 0
            and row.status.lower()
            not in {"expired", "cancelled", "canceled", "terminated", "inactive"}
        ]
        contract = max(
            candidates,
            key=lambda row: (
                row.source == "oci:onesubscription",
                row.status.lower() == "active",
                row.start_date,
            ),
            default=None,
        )
    if not contract:
        return {
            "contract": None,
            "periods": [],
            "diagnostics": diagnostics(db),
            "currencies": [],
        }
    # Include revision in cache key: fresh manual contracts/syncs do not leave a stale dashboard for ten minutes.
    latest = (
        db.query(SubscriptionPeriod.computed_at)
        .filter_by(contract_id=contract.id, mode=mode)
        .order_by(SubscriptionPeriod.computed_at.desc())
        .first()
    )
    sync_revision = (
        db.query(SubscriptionSyncRun)
        .order_by(SubscriptionSyncRun.started_at.desc())
        .first()
    )
    revision = [sync_revision.id, sync_revision.status] if sync_revision else None
    key = (
        "commitments_terms_v2_"
        + hashlib.sha256(
            json.dumps(
                [
                    principal.username,
                    contract.id,
                    contract.computed_at.isoformat(),
                    str(latest),
                    revision,
                    mode,
                    region,
                    date.today().isoformat(),
                ]
            ).encode()
        ).hexdigest()
    )
    cached = get_cached(key)
    if cached is not None:
        return cached
    applicable = spend_eligible(contract)
    models = (
        (
            db.query(SubscriptionPeriod)
            .filter_by(contract_id=contract.id, mode=mode)
            .order_by(SubscriptionPeriod.start_date)
            .all()
        )
        if applicable
        else []
    )
    periods = [period_json(row, contract.currency, region) for row in models]
    today = datetime.now(UTC).date()
    active = next(
        (
            row
            for row in periods
            if row["start_date"] <= today.isoformat() < row["end_date_exclusive"]
        ),
        None,
    )
    all_complete = bool(periods) and all(row["complete"] for row in periods)
    consumed = (
        sum((D(row["actual"]) for row in periods), Decimal(0)) if all_complete else None
    )
    elapsed = max(
        1,
        (min(today + timedelta(days=1), contract.end_date) - contract.start_date).days,
    )
    daily = consumed / D(elapsed) if consumed is not None else None
    forecast = (
        daily * D((contract.end_date - contract.start_date).days)
        if daily is not None
        else None
    )
    total = D(contract.total_value) if contract.total_value is not None else None
    remaining = total - consumed if total is not None and consumed is not None else None
    days_left = max(0, (contract.end_date - today).days)
    age = (
        datetime.now(UTC) - contract.computed_at.replace(tzinfo=UTC)
    ).total_seconds() / 3600
    if models:
        age = max(
            age,
            (
                datetime.now(UTC)
                - min(row.computed_at for row in models).replace(tzinfo=UTC)
            ).total_seconds()
            / 3600,
        )
    alerts = []
    if not applicable:
        alerts.append(
            "OCI infrastructure spend does not apply to this SaaS or unclassified contract. No consumption or utilisation is calculated."
        )
    if total and forecast is not None and forecast > total * D("1.05"):
        alerts.append("Forecast exceeds commitment by more than 5% (linear estimate).")
    if (
        total
        and consumed is not None
        and consumed / total < D("0.6")
        and days_left < 90
    ):
        alerts.append("Utilisation is below 60% with fewer than 90 days left.")
    if age > 48:
        alerts.append("Subscription or spend data is older than 48 hours.")
    if not all_complete:
        alerts.append(
            "Spend is incomplete or has not synced. Missing data is not shown as zero."
        )
    cumulative_actual = cumulative_allowance = Decimal(0)
    cumulative = []
    known = True
    for row in periods:
        period_start = date.fromisoformat(row["start_date"])
        period_end = date.fromisoformat(row["end_date_exclusive"])
        observed_end = min(period_end, today + timedelta(days=1))
        fraction = D((observed_end - period_start).days) / D(
            (period_end - period_start).days
        )
        cumulative_allowance += D(row["allowance"]) * fraction
        known = known and row["actual"] is not None
        if known:
            cumulative_actual += D(row["actual"])
        cumulative.append(
            {
                "date": observed_end.isoformat(),
                "committed": float(cumulative_allowance) if total is not None else None,
                "actual": float(cumulative_actual) if known else None,
                "forecast": None,
            }
        )
    if cumulative and forecast is not None:
        cumulative[-1]["forecast"] = float(consumed)
        cumulative.append(
            {
                "date": contract.end_date.isoformat(),
                "committed": float(total) if total is not None else None,
                "actual": None,
                "forecast": float(forecast),
            }
        )
    result = {
        "contract": contract_json(contract),
        "currencies": [contract.currency],
        "periods": periods,
        "active_period": active,
        "consumed_to_date": float(consumed) if consumed is not None else None,
        "remaining": float(remaining) if remaining is not None else None,
        "utilisation_pct": (
            float(consumed / total * 100) if total and consumed is not None else None
        ),
        "daily_burn": float(daily) if daily is not None else None,
        "forecast_term_end": float(forecast) if forecast is not None else None,
        "projected_overage": (
            float(max(Decimal(0), forecast - total))
            if forecast is not None and total is not None
            else None
        ),
        "projected_underuse": (
            float(max(Decimal(0), total - forecast))
            if forecast is not None and total is not None
            else None
        ),
        "days_remaining": days_left,
        "cumulative": cumulative,
        "alerts": alerts,
        "diagnostics": diagnostics(db),
        "computed_at": max(
            (row.computed_at for row in models), default=contract.computed_at
        ).isoformat(),
        "meta": {
            "actual_source": "OCI Usage API COST",
            "spend_scope": "tenancy" if not region or region == "all" else "region",
            "comparison": "Tenancy spend compared with selected contract; OCI COST does not prove contract attribution. Do not add overlapping contracts.",
            "allowance_scope": "whole contract (unchanged by region filter)",
            "end_dates": "exclusive UTC",
            "cache_ttl_seconds": 600,
            "estimates": ["linear_forecast", "allowance_proration"]
            + (["manual_contract"] if contract.source == "manual" else []),
            "payg_rate_spend": None,
            "payg_note": "Unavailable without a compatible OCI PAYG rate card and quantities; never inferred from discounted billed cost.",
            "credit_expiry": "Unavailable: credit aggregate query does not provide dated future balances.",
        },
    }
    set_cached(key, result, 600)
    return result


@router.get("/overview")
def overview(
    contract_id: Optional[str] = None,
    mode: Literal["subscription", "calendar"] = "subscription",
    region: Optional[str] = None,
    token: Optional[str] = Cookie(None, alias="access_token"),
    db: Session = Depends(get_db),
):
    principal = authorize(db, token)
    return {"success": True, "data": view(db, contract_id, mode, region, principal)}


@router.get("/periods")
def periods(
    contract_id: Optional[str] = None,
    months: int = Query(12, ge=1, le=120),
    mode: Literal["subscription", "calendar"] = "subscription",
    region: Optional[str] = None,
    token: Optional[str] = Cookie(None, alias="access_token"),
    db: Session = Depends(get_db),
):
    principal = authorize(db, token)
    data = view(db, contract_id, mode, region, principal)
    return {
        "success": True,
        "data": data["periods"][-months:],
        "meta": {
            "end_dates": "exclusive UTC",
            "estimates": ["allowance_proration", "linear_forecast"],
        },
    }


@router.get("/breakdown")
def breakdown(
    period: str,
    group_by: Literal["service", "compartment", "team"] = "service",
    region: Optional[str] = None,
    token: Optional[str] = Cookie(None, alias="access_token"),
    db: Session = Depends(get_db),
):
    principal = authorize(db, token)
    row = db.get(SubscriptionPeriod, period)
    if not row:
        raise HTTPException(404, "Period not found")
    contract = db.get(SubscriptionContract, row.contract_id)
    if not spend_eligible(contract):
        raise HTTPException(
            422,
            "OCI resource spend does not apply to this SaaS or unclassified contract",
        )
    cache_key = (
        "commitment_breakdown_terms_v2_"
        + hashlib.sha256(
            json.dumps(
                [principal.username, period, group_by, region, str(row.computed_at)]
            ).encode()
        ).hexdigest()
    )
    cached = get_cached(cache_key)
    if cached is not None:
        return cached
    contract = db.get(SubscriptionContract, row.contract_id)
    names = (
        {c.id: c.path or c.name for c in db.query(Compartment).all()}
        if group_by == "compartment"
        else {}
    )
    totals = {}
    detail = row.details or {}
    facts = detail.get("facts", [])
    complete = detail.get("complete", False)
    if group_by == "team" and "breakdown_facts" in detail:
        facts = detail.get("breakdown_facts") or []
        complete = complete and detail.get("breakdown_facts") is not None
    for fact in facts:
        if fact["currency"] != contract.currency or (
            region and region != "all" and fact["region"] != region
        ):
            continue
        name = fact.get(group_by) or "Unallocated"
        totals[name] = totals.get(name, Decimal(0)) + D(fact["amount"])
    items = sorted(totals.items(), key=lambda item: item[1], reverse=True)
    selected = items[:10]
    if len(items) > 10:
        selected.append(("Other", sum((value for _, value in items[10:]), Decimal(0))))
    result = {
        "success": True,
        "data": [
            {
                "name": names.get(name, name),
                "id": name,
                "actual": float(value),
                "allowance_share_pct": (
                    float(value / D(row.allowance) * 100) if row.allowance else None
                ),
            }
            for name, value in selected
        ],
        "meta": {
            "currency": contract.currency,
            "complete": complete,
            "basis": "Actual consumption / whole monthly allowance; not an assigned team budget",
            "source": "OCI Usage API COST",
        },
    }

    set_cached(cache_key, result, 600)
    return result


@router.get("/export")
def export_periods(
    contract_id: str,
    mode: Literal["subscription", "calendar"] = "subscription",
    format: Literal["csv", "xlsx"] = "csv",
    region: Optional[str] = None,
    token: Optional[str] = Cookie(None, alias="access_token"),
    db: Session = Depends(get_db),
):
    """Use the existing configured export directory and workbook/download conventions."""
    import csv
    from pathlib import Path
    from fastapi.responses import FileResponse
    from openpyxl import Workbook
    from core.config import get_settings

    principal = authorize(db, token)
    data = view(db, contract_id, mode, region, principal)
    if not data["contract"]:
        raise HTTPException(404, "Contract not found")
    folder = Path(get_settings().export_dir)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"commitment-periods-{uuid.uuid4()}.{format}"
    columns = [
        "contract_id",
        "source",
        "currency",
        "mode",
        "region",
        "start_date",
        "end_date_exclusive",
        "allowance_estimate",
        "charges",
        "credits",
        "actual",
        "forecast_estimate",
        "computed_at",
    ]
    rows = []
    for period in data["periods"]:
        values = [
            contract_id,
            data["contract"]["source"],
            data["contract"]["currency"],
            mode,
            region or "all",
            period["start_date"],
            period["end_date_exclusive"],
            period["allowance"],
            period["charges"],
            period["credits"],
            period["actual"],
            period["forecast"],
            period["computed_at"],
        ]
        rows.append(
            [
                (
                    ("'" + v)
                    if isinstance(v, str) and v.startswith(("=", "+", "-", "@"))
                    else v
                )
                for v in values
            ]
        )
    if format == "csv":
        with path.open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.writer(handle)
            writer.writerow(columns)
            writer.writerows(rows)
        media = "text/csv"
    else:
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Commitment periods"
        sheet.append(columns)
        for row in rows:
            sheet.append(row)
        workbook.save(path)
        media = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    return FileResponse(path, filename=path.name, media_type=media)


@router.get("/contracts/{contract_id}/lines")
def contract_lines(
    contract_id: str,
    token: Optional[str] = Cookie(None, alias="access_token"),
    db: Session = Depends(get_db),
):
    authorize(db, token)
    row = db.get(SubscriptionContract, contract_id)
    if not row or not visible(row):
        raise HTTPException(404, "Term not found")
    lines = (
        db.query(SubscriptionContractLine)
        .filter_by(contract_id=contract_id)
        .order_by(SubscriptionContractLine.start_date)
        .limit(200)
        .all()
    )
    return {
        "success": True,
        "data": [
            {
                "id": line.id,
                "start_date": line.start_date.isoformat(),
                "end_date": line.end_date.isoformat(),
                "value": (
                    float(line.total_value) if line.total_value is not None else None
                ),
                "currency": line.currency,
                "status": line.status,
                "subscribed_service_id": (line.details or {}).get(
                    "subscribed_service_id"
                ),
                "order_line_id": (line.details or {}).get("order_line_id"),
            }
            for line in lines
        ],
        "meta": {"source": "Preserved OCI service lines", "limit": 200},
    }

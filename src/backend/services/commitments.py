"""Commitment accounting: UTC half-open periods, explicit estimates, currency-safe OCI facts."""

from __future__ import annotations
import calendar
import hashlib
import logging
import re
import uuid
from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from sqlalchemy import text
from core.models import (
    SubscriptionContract,
    SubscriptionPeriod,
    SubscriptionSyncRun,
    Resource,
    JobRun,
)
from services.cost_calculator import get_cost_calculator
from services.oci_client import get_oci_client
from services.event_logger import redact_sensitive
from services.subscription_sources import discover, POLICIES
from services.allocation import evaluate_allocation, load_enabled_rules

logger = logging.getLogger(__name__)


def D(value):
    return Decimal(str(value or 0))


def month_at(anchor: date, offset: int) -> date:
    index = anchor.year * 12 + anchor.month - 1 + offset
    year, month = divmod(index, 12)
    return date(
        year, month + 1, min(anchor.day, calendar.monthrange(year, month + 1)[1])
    )


def windows(start: date, end: date, mode="subscription"):
    anchor = start if mode == "subscription" else start.replace(day=1)
    index = 0
    while month_at(anchor, index) < end:
        left, right = month_at(anchor, index), month_at(anchor, index + 1)
        yield max(start, left), min(end, right)
        index += 1


def allowance(contract, start, end):
    """Allocate each anniversary month's allowance by its actual days; preserve calendar splits."""
    if contract.total_value is None:
        return None
    base = D(contract.total_value) / D(contract.term_months)
    value = Decimal(0)
    for i, (left, right) in enumerate(windows(contract.start_date, contract.end_date)):
        overlap = max(0, (min(right, end) - max(left, start)).days)
        nominal_days = (
            month_at(contract.start_date, i + 1) - month_at(contract.start_date, i)
        ).days
        value += base * D(overlap) / D(nominal_days)
    return value


def parse_date(value):
    return date.fromisoformat(str(value)[:10])


def category(raw):
    explicit = raw.get("spend_category")
    if explicit in {"oci_infrastructure", "saas", "unknown"}:
        return explicit
    names = " ".join(
        str(raw.get(key) or "")
        for key in ("service_name", "parent_service_name", "organization_service_name")
    )
    compact = re.sub(r"[^a-z0-9]", "", names.lower())
    if "universalcredits" in compact or "cloudcm" in compact:
        return "oci_infrastructure"
    if any(
        word in names.lower().split()
        for word in ("fusion", "erp", "hcm", "epm", "planning")
    ):
        return "saas"
    return "unknown"


def spend_eligible(contract):
    details = contract.details or {}
    if contract.source == "manual":
        return (
            details.get("spend_category", "oci_infrastructure") == "oci_infrastructure"
        )
    return (
        category(
            {
                **(details.get("source_evidence") or {}),
                **(
                    {"spend_category": details["spend_category"]}
                    if "spend_category" in details
                    else {}
                ),
            }
        )
        == "oci_infrastructure"
    )


def term_candidates(raw):
    """An auto-renewing parent need not have dates. Financial terms live in child services.

    The separately listed service ID is authoritative for commitment lookups; embedded IDs
    may be order-line IDs. Preserve both without substituting one for the other.
    """
    if raw.get("source") != "oci:onesubscription":
        return [raw]
    embedded = raw.get("subscribed_services") or []
    detailed = raw.get("services") or []
    services = []
    matched = set()
    for service in detailed:
        match = next(
            (
                row
                for row in embedded
                if str(row.get("id"))
                in {str(service.get("id")), str(service.get("order_line_id"))}
            ),
            None,
        )
        if match:
            matched.add(str(match.get("id")))
        services.append(
            {
                **(match or {}),
                **{key: value for key, value in service.items() if value is not None},
                "subscribed_service_id": service.get("id"),
                "order_line_id": service.get("order_line_id")
                or (match or {}).get("id"),
            }
        )
    services.extend(
        {**row, "subscribed_service_id": None, "order_line_id": row.get("id")}
        for row in embedded
        if str(row.get("id")) not in matched
    )
    if not services:
        return [raw]
    result = []
    for service in services:
        identity = service.get("subscribed_service_id") or service.get("order_line_id")
        if identity is None:
            continue
        start = service.get("time_start")
        parent_name = (
            raw.get("service_name")
            or raw.get("organization_service_name")
            or "Subscription"
        )
        result.append(
            {
                **raw,
                **service,
                "id": f"{raw['id']}:service:{identity}",
                "service_name": (
                    f"{parent_name}, term {str(start)[:4]}"
                    if start
                    else f"{parent_name}, undated term"
                ),
                "total_value": service.get("total_value"),
                "parent_service_name": parent_name,
                "parent_subscription_id": raw["id"],
                "source": raw["source"],
                "currency": service.get("currency") or raw.get("currency"),
                "subscribed_services": [],
                "services": [],
                "spend_category": category(raw),
            }
        )
    return result


def normalize(raw, now):
    """Only explicit subscription monetary totals are eligible. SKU quantity is never currency."""
    currency = (
        raw.get("currency_code")
        or raw.get("cloud_amount_currency")
        or raw.get("currency")
    )
    if isinstance(currency, dict):
        currency = currency.get("iso_code")
    start, end = raw.get("time_start") or raw.get("start_date"), raw.get(
        "time_end"
    ) or raw.get("end_date")
    if not start or not end or not currency or not raw.get("id"):
        return None
    try:
        currency = str(currency).strip().upper()
        if not re.fullmatch(r"[A-Z]{3}", currency):
            return None
        start, end = parse_date(start), parse_date(end)
        if end <= start:
            return None
        months = max(1, (end.year - start.year) * 12 + end.month - start.month)
        if month_at(start, months) < end:
            months += 1
        amount = raw.get("total_value")
        services = raw.get("subscribed_services") or []
        if (
            amount is None
            and services
            and all(
                service.get("total_value") is not None
                and str(service.get("time_start") or "")[:10] == start.isoformat()
                and str(service.get("time_end") or "")[:10] == end.isoformat()
                for service in services
            )
        ):
            amount = sum(
                (D(service["total_value"]) for service in services), Decimal(0)
            )
        # Legacy helper's SubscribedService net-price/quantity product and OSP dates are not reliable contract evidence.
        if raw.get("legacy_fallback"):
            amount = None
        amount = D(amount) if amount is not None else None
        if amount is not None and (not amount.is_finite() or amount < 0):
            amount = None
        return dict(
            id=hashlib.sha256(
                f"{raw['source']}:{raw['id']}:{start.isoformat()}:{end.isoformat()}".encode()
            ).hexdigest(),
            source=raw["source"],
            name=raw.get("service_name") or str(raw["id"]),
            status=raw.get("status") or raw.get("lifecycle_state") or "unknown",
            start_date=start,
            end_date=end,
            currency=str(currency).strip().upper(),
            total_value=amount,
            term_months=months,
            computed_at=now,
            details={
                "external_id": raw["id"],
                "payment_model": raw.get("payment_model"),
                "monetary_value_available": amount is not None,
                "spend_category": category(raw),
                "parent_subscription_id": raw.get("parent_subscription_id"),
                "classic_subscription_id": raw.get("classic_subscription_id"),
                "organization_id": raw.get("organization_id"),
                "subscribed_service_id": raw.get("subscribed_service_id"),
                "order_line_id": raw.get("order_line_id"),
                "source_evidence": raw,
            },
        )
    except (ValueError, TypeError, ArithmeticError):
        return None


def _facts(rows, db, enrich_resources=True):
    resources = (
        {r.ocid: r for r in db.query(Resource).all()} if enrich_resources else {}
    )
    rules = load_enabled_rules(db) if enrich_resources else []
    facts = defaultdict(Decimal)
    for item in rows:
        currency = str(item.get("currency") or "").strip().upper()
        value = D(item.get("computed_amount"))
        if not currency:
            if value == 0:
                continue
            raise ValueError("Nonzero OCI cost has no currency")
        model = resources.get(item.get("resource_id"))
        allocation = evaluate_allocation(model, rules) if model else None
        key = (
            str(item.get("time_usage_started") or "")[:10],
            currency,
            item.get("region") or (model.region if model else None),
            item.get("service") or "Unattributed",
            model.compartment_id if model else item.get("compartment_id"),
            allocation.team if allocation else None,
            allocation.app if allocation else None,
            allocation.env if allocation else None,
            "credit" if value < 0 else "charge",
        )
        if not key[0]:
            raise ValueError("OCI cost row has no usage date")
        facts[key] += value
    return [
        dict(
            zip(
                (
                    "date",
                    "currency",
                    "region",
                    "service",
                    "compartment",
                    "team",
                    "app",
                    "env",
                    "kind",
                ),
                key,
            ),
            amount=str(value),
        )
        for key, value in facts.items()
    ]


def sync(db):
    now = datetime.now(UTC)
    # Distributed advisory lock on PostgreSQL; worker concurrency alone is insufficient.
    locked = False
    lease_connection = None
    if db.bind.dialect.name == "postgresql":
        lease_connection = db.bind.connect()
        locked = bool(
            lease_connection.execute(
                text("SELECT pg_try_advisory_xact_lock(230017)")
            ).scalar()
        )
        if not locked:
            lease_connection.close()
            return {"status": "already_running"}
    run = SubscriptionSyncRun(
        id=str(uuid.uuid4()), status="running", started_at=now, sources={}
    )
    reports = {}
    try:
        db.add(run)
        db.commit()
        try:
            manual_ids = [
                (row.details or {}).get("oci_subscription_id")
                for row in db.query(SubscriptionContract)
                .filter_by(source="manual")
                .all()
            ]
            raw, reports = discover(
                get_oci_client(), subscription_ids=[sid for sid in manual_ids if sid]
            )
            candidates = [
                candidate for item in raw for candidate in term_candidates(item)
            ]
            for item in candidates:
                values = normalize(item, now)
                if not values:
                    reports[f"normalization:{item.get('id', 'unknown')}"] = {
                        "status": "incomplete",
                        "error": "Missing confirmed dates, currency or identifier; manual contract is available.",
                    }
                    continue
                if values["total_value"] is None:
                    reports[f"monetary-value:{item.get('id', 'unknown')}"] = {
                        "status": "incomplete",
                        "error": "Subscription metadata returned, but no confirmed monetary commitment amount. SKU quantities and billing installments are not substituted; manual entry is available.",
                    }
                model = db.get(
                    SubscriptionContract, values["id"]
                ) or SubscriptionContract(id=values["id"])
                for key, value in values.items():
                    setattr(model, key, value)
                db.add(model)
            db.commit()
        except Exception as exc:
            logger.exception("subscription_discovery_failed sync_id=%s", run.id)
            reports["oci:discovery"] = {
                "status": "unavailable",
                "error": redact_sensitive(str(exc))[:4000],
                "policies": POLICIES["oci:organizations"],
            }
            db.rollback()
        calc = get_cost_calculator()
        today = now.date()
        contracts = (
            db.query(SubscriptionContract)
            .filter(
                SubscriptionContract.start_date <= today,
                SubscriptionContract.end_date > today,
                SubscriptionContract.total_value > 0,
            )
            .all()
        )
        # Fetch each calendar window once, shared by overlapping contracts. Chunk to meet OCI range limits.
        monthly_facts = {}
        retention_start = month_at(today.replace(day=1), -12)
        detail_facts = {}
        for contract in contracts:
            if not spend_eligible(contract) or contract.status.lower() in {
                "expired",
                "cancelled",
                "canceled",
                "terminated",
                "inactive",
            }:
                continue
            left = contract.start_date.replace(day=1)
            while left < min(contract.end_date, today + timedelta(days=1)):
                right = min(month_at(left, 1), today + timedelta(days=1))
                key = (left, right)
                if key not in monthly_facts and right <= month_at(
                    today.replace(day=1), -12
                ):
                    saved = (
                        db.query(SubscriptionPeriod)
                        .filter_by(
                            contract_id=contract.id,
                            mode="calendar",
                            start_date=left,
                            end_date=right,
                        )
                        .first()
                    )
                    if saved and (saved.details or {}).get("complete"):
                        monthly_facts[key] = saved.details.get("facts", [])
                if key not in monthly_facts and right <= retention_start:
                    monthly_facts[key] = None
                    reports[f"oci:usage/history:{left}"] = {
                        "status": "outside_retention",
                        "error": "Outside the 13-month Usage API window with no complete saved snapshot; historical spend remains unknown, not zero.",
                    }
                if key not in monthly_facts:
                    try:
                        rows = calc.get_usage_summary(
                            datetime.combine(left, datetime.min.time(), UTC),
                            datetime.combine(right, datetime.min.time(), UTC),
                            granularity="DAILY",
                            group_by=["service", "compartmentId", "region"],
                        )
                        monthly_facts[key] = _facts(rows, db, enrich_resources=False)
                    except Exception as exc:
                        logger.exception(
                            "subscription_usage_failed sync_id=%s start=%s",
                            run.id,
                            left,
                        )
                        reports[f"oci:usage/{left}"] = {
                            "status": "unavailable",
                            "error": redact_sensitive(str(exc))[:4000],
                            "policies": POLICIES["oci:usage"],
                        }
                        monthly_facts[key] = None
                left = month_at(left, 1)
            all_facts = [
                row
                for rows in monthly_facts.values()
                if rows is not None
                for row in rows
                if contract.start_date.isoformat()
                <= row["date"]
                < contract.end_date.isoformat()
            ]
            for mode in ("subscription", "calendar"):
                for start, end in windows(contract.start_date, contract.end_date, mode):
                    if start > today:
                        continue
                    keys = [
                        key
                        for key in monthly_facts
                        if key[0] < min(end, today + timedelta(days=1))
                        and key[1] > start
                    ]
                    complete = bool(keys) and all(
                        monthly_facts[key] is not None for key in keys
                    )
                    facts = [
                        row
                        for row in all_facts
                        if start.isoformat() <= row["date"] < end.isoformat()
                    ]
                    breakdown_facts = None
                    if start <= today < end:
                        detail_key = (start, min(end, today + timedelta(days=1)))
                        if detail_key not in detail_facts:
                            try:
                                rows = calc.get_usage_summary(
                                    datetime.combine(
                                        detail_key[0], datetime.min.time(), UTC
                                    ),
                                    datetime.combine(
                                        detail_key[1], datetime.min.time(), UTC
                                    ),
                                    granularity="MONTHLY",
                                    group_by=["resourceId", "service", "region"],
                                )
                                detail_facts[detail_key] = _facts(rows, db)
                            except Exception as exc:
                                detail_facts[detail_key] = None
                                reports[f"oci:usage/detail:{start}"] = {
                                    "status": "unavailable",
                                    "error": redact_sensitive(str(exc))[:4000],
                                }
                        breakdown_facts = detail_facts[detail_key]
                    actual = (
                        sum(
                            (
                                D(row["amount"])
                                for row in facts
                                if row["currency"] == contract.currency
                            ),
                            Decimal(0),
                        )
                        if complete
                        else None
                    )
                    if breakdown_facts is not None and actual is not None:
                        detailed_actual = sum(
                            (
                                D(row["amount"])
                                for row in breakdown_facts
                                if row["currency"] == contract.currency
                            ),
                            Decimal(0),
                        )
                        if abs(detailed_actual - actual) > Decimal("0.01"):
                            reports[f"oci:usage/detail-reconciliation:{start}"] = {
                                "status": "incomplete",
                                "error": "Resource breakdown does not reconcile with service aggregates for this window/currency; team chart withheld.",
                            }
                            breakdown_facts = None
                    elapsed = max(1, (min(end, today + timedelta(days=1)) - start).days)
                    pid = hashlib.sha256(
                        f"{contract.id}:{mode}:{start}".encode()
                    ).hexdigest()
                    period = db.get(SubscriptionPeriod, pid) or SubscriptionPeriod(
                        id=pid
                    )
                    (
                        period.contract_id,
                        period.mode,
                        period.start_date,
                        period.end_date,
                    ) = (contract.id, mode, start, end)
                    period.allowance, period.actual = (
                        allowance(contract, start, end),
                        actual,
                    )
                    period.forecast = (
                        actual * D((end - start).days) / D(elapsed)
                        if actual is not None
                        else None
                    )
                    period.computed_at = now
                    period.details = {
                        "facts": facts,
                        "breakdown_facts": breakdown_facts,
                        "detail_granularity": "MONTHLY",
                        "summary_granularity": "DAILY service/compartment/region",
                        "complete": complete,
                        "elapsed_days": elapsed,
                        "actual_basis": "OCI Usage API tenancy spend; not contract-attributed",
                        "estimates": ["allowance_proration", "linear_forecast"],
                    }
                    db.add(period)
                db.commit()  # checkpoint each contract/mode
        # Credit balances are an independent source and never added to COST (which already includes adjustments).
        for kind in ("CREDIT", "EXPIREDCREDIT", "ALLCREDIT"):
            try:
                rows = calc.get_usage_summary(
                    now.replace(day=1),
                    now + timedelta(days=1),
                    granularity="MONTHLY",
                    group_by=None,
                    query_type=kind,
                )
                totals = defaultdict(Decimal)
                for row in rows:
                    currency = str(row.get("currency") or "").strip().upper()
                    if currency:
                        totals[currency] += D(row.get("computed_amount"))
                reports[f"oci:usage/{kind}"] = {
                    "status": "ok" if rows else "empty",
                    "totals": {key: str(value) for key, value in totals.items()},
                    "note": "Separate credit query; not added to COST. Expiry dates unavailable from this aggregate.",
                }
            except Exception as exc:
                reports[f"oci:usage/{kind}"] = {
                    "status": "unavailable",
                    "error": redact_sensitive(str(exc))[:4000],
                    "policies": POLICIES["oci:usage"],
                }
        run = db.get(SubscriptionSyncRun, run.id)
        run.status = (
            "partial"
            if any(
                value.get("status")
                in {
                    "unavailable",
                    "forbidden_or_not_found",
                    "incomplete",
                    "needs_identifier",
                    "outside_retention",
                }
                for value in reports.values()
            )
            else "succeeded"
        )
        run.sources, run.finished_at = reports, datetime.now(UTC)
        db.commit()
        return {"sync_run_id": run.id, "status": run.status, "sources": reports}
    except Exception as exc:
        logger.exception("subscription_sync_failed sync_id=%s", run.id)
        db.rollback()
        run = db.get(SubscriptionSyncRun, run.id) or run
        db.add(run)
        run.status, run.finished_at = "failed", datetime.now(UTC)
        run.sources = {
            **reports,
            "sync": {"status": "failed", "error": redact_sensitive(str(exc))[:4000]},
        }
        db.commit()
        raise
    finally:
        if locked:
            try:
                lease_connection.rollback()
            finally:
                lease_connection.close()


def queue_sync(db, trigger="manual"):
    from worker import celery_app
    from core.models import Setting

    setting = db.get(Setting, 1)
    if setting and not setting.commitments_enabled:
        return None
    job = JobRun(
        id=str(uuid.uuid4()),
        job_type="subscription_sync",
        status="queued",
        progress=0,
        params={"trigger": trigger},
        created_at=datetime.now(UTC),
    )
    db.add(job)
    db.commit()
    try:
        celery_app.send_task(
            "jobs.subscription_sync", args=[job.id, job.params], queue="heavy"
        )
    except Exception:
        job.status, job.error_message = "failed", "Unable to enqueue subscription sync"
        db.commit()
        raise
    return job.id


def scheduled_sync():
    from core.database import SessionLocal

    with SessionLocal() as db:
        queue_sync(db, "daily")

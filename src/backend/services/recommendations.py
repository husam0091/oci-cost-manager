"""Deterministic, explainable optimization recommendations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
from typing import Any, Iterable, Optional

from sqlalchemy.orm import Session

from core.models import Compartment, Resource
from services import get_cost_calculator
from services.allocation import evaluate_allocation, load_enabled_rules


@dataclass
class Recommendation:
    recommendation_id: str
    category: str
    type: str
    resource_ref: str
    resource_name: str
    compartment_id: Optional[str]
    compartment_name: Optional[str]
    team: str
    app: str
    env: str
    current_cost: float
    estimated_savings: float
    confidence: str
    reason: str
    recommendation: str
    why_flagged: list[str]
    next_steps: list[str]
    history: dict[str, float]


def _safe_pct(delta: float, base: float) -> float:
    return (delta / base * 100.0) if base else 0.0


def _short_ocid(value: Optional[str]) -> str:
    if not value:
        return "unknown"
    parts = str(value).split(".")
    return parts[-1][-16:] if parts else str(value)[-16:]


def _parse_datetime(value: Any) -> Optional[datetime]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    if isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return dt if dt.tzinfo else dt.replace(tzinfo=UTC)
        except ValueError:
            return None
    return None


def _confidence_rank(value: str) -> int:
    return {"high": 0, "medium": 1, "low": 2}.get(value, 3)


def _deterministic_id(category: str, rec_type: str, resource_ref: str, reason: str) -> str:
    payload = f"{category}|{rec_type}|{resource_ref}|{reason}"
    digest = hashlib.sha1(payload.encode("utf-8")).hexdigest()[:14]
    return f"rec_{digest}"


def _to_item(
    *,
    category: str,
    rec_type: str,
    resource_ref: str,
    resource_name: str,
    compartment_id: Optional[str],
    compartment_name: Optional[str],
    team: str,
    app: str,
    env: str,
    current_cost: float,
    estimated_savings: float,
    confidence: str,
    reason: str,
    recommendation: str,
    why_flagged: Iterable[str],
    next_steps: Iterable[str],
    history: dict[str, float],
) -> Recommendation:
    reason_text = reason.strip() or "no_reason_provided"
    rec_id = _deterministic_id(category, rec_type, resource_ref, reason_text)
    return Recommendation(
        recommendation_id=rec_id,
        category=category,
        type=rec_type,
        resource_ref=resource_ref,
        resource_name=resource_name,
        compartment_id=compartment_id,
        compartment_name=compartment_name,
        team=team,
        app=app,
        env=env,
        current_cost=round(max(current_cost, 0.0), 2),
        estimated_savings=round(max(estimated_savings, 0.0), 2),
        confidence=confidence,
        reason=reason_text,
        recommendation=recommendation,
        why_flagged=list(why_flagged),
        next_steps=list(next_steps),
        history=history,
    )


def _resource_name(resource: Optional[Resource], rid: Optional[str]) -> str:
    if resource and resource.name:
        return resource.name
    return _short_ocid(rid)


def _license_kind(resource: Optional[Resource], sku_text: str) -> Optional[str]:
    text = sku_text.lower()
    details = resource.details if resource and resource.details else {}
    image_name = str(details.get("image_name") or "").lower()
    rtype = (resource.type or "").lower() if resource else ""
    if "sql server" in text or "microsoft sql" in text or rtype == "sql_server":
        return "sql"
    if "windows" in text or "windows" in image_name or rtype == "windows_server":
        return "windows"
    return None


def generate_recommendations(
    *,
    db: Session,
    start: datetime,
    end_exclusive: datetime,
) -> dict[str, Any]:
    calc = get_cost_calculator()
    prev_end = start
    prev_start = prev_end - (end_exclusive - start)
    period_days = max((end_exclusive - start).days, 1)

    current_rows = calc.get_costs_by_resource(start, end_exclusive, include_skus=True)
    previous_rows = calc.get_costs_by_resource(prev_start, prev_end, include_skus=True)
    prev_by_id = {r.get("resource_id"): float(r.get("total_cost") or 0.0) for r in previous_rows}

    resource_ids = [r.get("resource_id") for r in current_rows if r.get("resource_id")]
    resources = db.query(Resource).filter(Resource.ocid.in_(resource_ids)).all() if resource_ids else []
    resources_by_id = {r.ocid: r for r in resources}
    compartment_names = {c.id: c.name for c in db.query(Compartment).all()}
    rules = load_enabled_rules(db)

    recommendations: list[Recommendation] = []
    license_windows_count = 0
    license_sql_count = 0
    license_windows_cost = 0.0
    license_sql_cost = 0.0

    for row in current_rows:
        rid = row.get("resource_id")
        current_cost = float(row.get("total_cost") or 0.0)
        previous_cost = float(prev_by_id.get(rid, 0.0))
        delta = current_cost - previous_cost
        delta_pct = _safe_pct(delta, previous_cost)
        skus = row.get("skus") or []
        sku_text = " ".join((s.get("sku_name") or "") for s in skus)

        resource = resources_by_id.get(rid)
        details = resource.details if resource and resource.details else {}
        rtype = (resource.type or "").lower() if resource else ""
        status = str(resource.status or "").upper() if resource else ""
        compartment_id = resource.compartment_id if resource else row.get("compartment_id")
        compartment_name = compartment_names.get(compartment_id or "", row.get("compartment_name") or "Unknown")

        alloc = evaluate_allocation(resource, rules, compartment_name=compartment_name, sku_text=sku_text)
        team = alloc.team
        app = alloc.app
        env = alloc.env
        resource_name = _resource_name(resource, rid)
        history = {
            "current": round(current_cost, 2),
            "previous": round(previous_cost, 2),
            "delta_abs": round(delta, 2),
            "delta_pct": round(delta_pct, 2),
        }

        # 1) Unattached resources and old backups.
        attachment = str(details.get("attachment_state") or "").upper()
        if rtype in {"block_volume", "boot_volume"} and attachment == "UNATTACHED":
            action = "delete" if rtype == "block_volume" else "review"
            recommendations.append(
                _to_item(
                    category="storage",
                    rec_type="unattached_resource",
                    resource_ref=rid or "unknown",
                    resource_name=resource_name,
                    compartment_id=compartment_id,
                    compartment_name=compartment_name,
                    team=team,
                    app=app,
                    env=env,
                    current_cost=current_cost,
                    estimated_savings=current_cost,
                    confidence="high",
                    reason=f"{rtype} is unattached and still accruing cost",
                    recommendation=f"{action} or reattach unused {rtype.replace('_', ' ')}",
                    why_flagged=[
                        f"Attachment state: {attachment or 'UNKNOWN'}",
                        f"Monthly cost: ${current_cost:.2f}",
                    ],
                    next_steps=[
                        "Validate data retention need",
                        "Snapshot if required, then remove or reattach",
                    ],
                    history=history,
                )
            )

        if rtype in {"volume_backup", "boot_volume_backup"}:
            created = _parse_datetime(details.get("time_created"))
            age_days = (datetime.now(UTC) - created).days if created else None
            if age_days is not None and age_days > 30:
                recommendations.append(
                    _to_item(
                        category="backup",
                        rec_type="orphaned_backup_retention",
                        resource_ref=rid or "unknown",
                        resource_name=resource_name,
                        compartment_id=compartment_id,
                        compartment_name=compartment_name,
                        team=team,
                        app=app,
                        env=env,
                        current_cost=current_cost,
                        estimated_savings=current_cost * 0.8,
                        confidence="high",
                        reason=f"Backup older than retention window ({age_days} days)",
                        recommendation="review and prune backup retention",
                        why_flagged=[
                            f"Backup age: {age_days} days",
                            "Retention policy threshold: 30 days",
                        ],
                        next_steps=[
                            "Check legal/compliance retention requirement",
                            "Delete expired backups per policy",
                        ],
                        history=history,
                    )
                )

        # 2) Idle or underutilized compute.
        looks_compute = rtype in {"compute", "windows_server", "sql_server"} or "instance" in rtype
        if looks_compute:
            shape = str(resource.shape or "").upper() if resource else ""
            ocpus = float(details.get("ocpus") or 0.0)
            low_usage_proxy = (
                status == "STOPPED"
                or ("E4" in shape and current_cost < 20.0)
                or ("E5" in shape and current_cost < 30.0)
                or (ocpus >= 4 and current_cost < 25.0)
            )
            if low_usage_proxy:
                action = "schedule" if status == "STOPPED" else "downsize"
                savings_ratio = 0.6 if status == "STOPPED" else 0.3
                recommendations.append(
                    _to_item(
                        category="compute",
                        rec_type="idle_or_underutilized_compute",
                        resource_ref=rid or "unknown",
                        resource_name=resource_name,
                        compartment_id=compartment_id,
                        compartment_name=compartment_name,
                        team=team,
                        app=app,
                        env=env,
                        current_cost=current_cost,
                        estimated_savings=current_cost * savings_ratio,
                        confidence="medium",
                        reason="Heuristic utilization proxy indicates low compute activity",
                        recommendation=f"{action} or review rightsizing policy",
                        why_flagged=[
                            f"Lifecycle status: {status or 'UNKNOWN'}",
                            f"Shape: {shape or 'UNKNOWN'}",
                            f"Monthly cost: ${current_cost:.2f}",
                        ],
                        next_steps=[
                            "Validate business-hour utilization",
                            "Right-size shape or add stop/start schedule",
                        ],
                        history=history,
                    )
                )

        # 3) Oversized storage.
        if rtype in {"block_volume", "boot_volume"}:
            size_gb = float(details.get("size_in_gbs") or 0.0)
            if size_gb >= 500:
                recommendations.append(
                    _to_item(
                        category="storage",
                        rec_type="oversized_storage",
                        resource_ref=rid or "unknown",
                        resource_name=resource_name,
                        compartment_id=compartment_id,
                        compartment_name=compartment_name,
                        team=team,
                        app=app,
                        env=env,
                        current_cost=current_cost,
                        estimated_savings=current_cost * 0.25,
                        confidence="medium",
                        reason=f"Volume size {int(size_gb)}GB exceeds optimization threshold",
                        recommendation="resize volume or reduce retained backups",
                        why_flagged=[
                            f"Volume size: {int(size_gb)} GB",
                            f"Attachment state: {attachment or 'UNKNOWN'}",
                        ],
                        next_steps=[
                            "Validate actual used capacity",
                            "Resize to observed peak + buffer",
                        ],
                        history=history,
                    )
                )

        # 4) License optimization signals (aggregated advisory).
        license_kind = _license_kind(resource, sku_text)
        if license_kind == "windows":
            license_windows_count += 1
            license_windows_cost += current_cost
        elif license_kind == "sql":
            license_sql_count += 1
            license_sql_cost += current_cost

    if license_windows_count > 0:
        recommendations.append(
            _to_item(
                category="license",
                rec_type="license_windows_signal",
                resource_ref="workload:windows",
                resource_name="Windows workloads",
                compartment_id=None,
                compartment_name=None,
                team="Unallocated",
                app="Unallocated",
                env="Unallocated",
                current_cost=license_windows_cost,
                estimated_savings=license_windows_cost * 0.15,
                confidence="low",
                reason=f"{license_windows_count} Windows workloads identified for license optimization review",
                recommendation="evaluate BYOL eligibility and workload consolidation",
                why_flagged=[
                    f"Detected Windows workloads: {license_windows_count}",
                    f"Estimated monthly license-related cost: ${license_windows_cost:.2f}",
                ],
                next_steps=[
                    "Validate license mobility rights",
                    "Consider shared host / consolidation plan",
                ],
                history={
                    "current": round(license_windows_cost, 2),
                    "previous": 0.0,
                    "delta_abs": round(license_windows_cost, 2),
                    "delta_pct": 0.0,
                },
            )
        )

    if license_sql_count > 0:
        recommendations.append(
            _to_item(
                category="license",
                rec_type="license_sql_signal",
                resource_ref="workload:sql",
                resource_name="SQL Server workloads",
                compartment_id=None,
                compartment_name=None,
                team="Unallocated",
                app="Unallocated",
                env="Unallocated",
                current_cost=license_sql_cost,
                estimated_savings=license_sql_cost * 0.20,
                confidence="low",
                reason=f"{license_sql_count} SQL Server workloads identified for licensing review",
                recommendation="evaluate BYOL and edition consolidation opportunities",
                why_flagged=[
                    f"Detected SQL workloads: {license_sql_count}",
                    f"Estimated monthly license-related cost: ${license_sql_cost:.2f}",
                ],
                next_steps=[
                    "Review SQL edition/license needs",
                    "Assess consolidation or managed alternatives",
                ],
                history={
                    "current": round(license_sql_cost, 2),
                    "previous": 0.0,
                    "delta_abs": round(license_sql_cost, 2),
                    "delta_pct": 0.0,
                },
            )
        )

    recommendations.sort(
        key=lambda r: (
            _confidence_rank(r.confidence),
            -r.estimated_savings,
            r.category,
            r.recommendation_id,
        )
    )

    return {
        "period": {
            "start_date": start.date().isoformat(),
            "end_date": (end_exclusive.date()).isoformat() if end_exclusive.hour or end_exclusive.minute else (end_exclusive.date().isoformat()),
            "days": period_days,
        },
        "items": recommendations,
    }


"""Conservative contract hygiene. Date overlap alone is never a financial identity."""

from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal
import hashlib
from core.models import (
    SubscriptionContract,
    SubscriptionContractLine,
    SubscriptionPeriod,
)


def visible(row):
    info = row.details or {}
    return (
        row.source != "oci:organizations"
        and not info.get("metadata_only")
        and not info.get("superseded_by")
        and row.total_value != 0
    )


def parent_id(row):
    info = row.details or {}
    raw = info.get("source_evidence") or {}
    return str(
        info.get("classic_subscription_id")
        or info.get("parent_subscription_id")
        or raw.get("classic_subscription_id")
        or raw.get("parent_subscription_id")
        or raw.get("subscription_number")
        or info.get("external_id")
        or row.id
    )


def term_identity(row):
    raw = (row.details or {}).get("source_evidence") or {}
    # A master agreement/order can span renewals. Only an explicit term identifier
    # is enough to join different date windows. An ordinary order_number is not.
    identity = raw.get("subscription_term_id") or raw.get("contract_term_id")
    return (
        (parent_id(row), row.currency, "term", str(identity))
        if identity
        else (
            parent_id(row),
            row.currency,
            "dates",
            row.start_date.isoformat(),
            row.end_date.isoformat(),
        )
    )


def group_label(row):
    if row.source == "manual":
        return "Manual"
    if row.end_date <= date.today() or row.status.lower() in {
        "expired",
        "terminated",
        "cancelled",
        "canceled",
    }:
        return "Expired terms"
    from services.commitments import spend_eligible

    return (
        "Infrastructure (Universal Credits)"
        if spend_eligible(row)
        else "SaaS (Fusion, EPM)"
    )


def consolidate(db, now):
    """Idempotently retain lines, hide old aliases and create one canonical term.

    Existing periods can be re-keyed only when their original full term boundaries
    exactly match the canonical term. Amounts are never added across snapshots.
    """
    from services.commitments import allowance

    all_rows = db.query(SubscriptionContract).all()
    metadata = defaultdict(list)
    candidates = []
    for row in all_rows:
        info = row.details or {}
        raw = info.get("source_evidence") or {}
        if row.source == "oci:organizations":
            metadata[parent_id(row)].append(
                {"name": row.name, "source": row.source, "evidence": raw}
            )
            continue
        if row.source != "oci:onesubscription" or info.get("canonical_term"):
            continue
        if not info.get("parent_subscription_id") and (
            raw.get("subscribed_services") or raw.get("services")
        ):
            row.details = {**info, "metadata_only": True}
            continue  # old aggregate parent must not be added to its own children
        candidates.append(row)
    groups = defaultdict(list)
    zero = []
    for row in candidates:
        if row.total_value == 0:
            zero.append(row)
        else:
            groups[term_identity(row)].append(row)
    for addon in zero:
        owners = [
            key
            for key, rows in groups.items()
            if key[:2] == (parent_id(addon), addon.currency)
            and min(row.start_date for row in rows) <= addon.start_date
            and max(row.end_date for row in rows) >= addon.end_date
        ]
        if len(owners) == 1:
            groups[owners[0]].append(addon)
        else:
            line = db.get(
                SubscriptionContractLine, addon.id
            ) or SubscriptionContractLine(id=addon.id)
            _save_line(db, line, addon, None)
            addon.details = {
                **(addon.details or {}),
                "metadata_only": True,
                "grouping_warning": "Zero addendum has no unique owning term; retained as an unassigned audit line.",
            }
    canonical_ids = []
    for key, rows in groups.items():
        contract_id = hashlib.sha256(
            ("canonical-term:" + repr(key)).encode()
        ).hexdigest()
        positive = [row for row in rows if row.total_value != 0]
        start, end = min(row.start_date for row in positive), max(
            row.end_date for row in positive
        )
        term = db.get(SubscriptionContract, contract_id) or SubscriptionContract(
            id=contract_id
        )
        exemplar = positive[0]
        raw = (exemplar.details or {}).get("source_evidence") or {}
        name = (
            raw.get("parent_service_name") or raw.get("service_name") or exemplar.name
        )
        name = name.split(", term ")[0]
        term.name = f"{name} · {start:%d %b %Y} – {end:%d %b %Y}"
        term.source, term.start_date, term.end_date = exemplar.source, start, end
        term.currency = exemplar.currency
        term.status = (
            "EXPIRED"
            if end <= now.date()
            else (
                "ACTIVE"
                if any(row.status.lower() == "active" for row in rows)
                else exemplar.status
            )
        )
        term.term_months = max(
            1,
            (end.year - start.year) * 12
            + end.month
            - start.month
            + (end.day > start.day),
        )
        term.total_value = (
            sum((row.total_value for row in rows), Decimal(0))
            if all(row.total_value is not None for row in rows)
            else None
        )
        term.computed_at = max(
            rows, key=lambda row: row.computed_at.replace(tzinfo=None)
        ).computed_at
        term.details = {
            **(exemplar.details or {}),
            "canonical_term": True,
            "superseded_by": None,
            "metadata_only": False,
            "grouping_basis": (
                "explicit_term_id"
                if key[2] == "term"
                else "identical_parent_currency_dates"
            ),
            "organizations_metadata": metadata.get(parent_id(exemplar), []),
            "source_line_ids": [row.id for row in rows],
        }
        db.add(term)
        db.flush()
        for row in rows:
            line = db.get(SubscriptionContractLine, row.id) or SubscriptionContractLine(
                id=row.id
            )
            _save_line(db, line, row, contract_id)
            # Preserve already reconciled usage exactly once; never sum the same
            # tenancy consumption for concurrent contractual service lines.
            if row.start_date == start and row.end_date == end:
                for period in (
                    db.query(SubscriptionPeriod).filter_by(contract_id=row.id).all()
                ):
                    new_id = hashlib.sha256(
                        f"{contract_id}:{period.mode}:{period.start_date}".encode()
                    ).hexdigest()
                    if db.get(SubscriptionPeriod, new_id) is None:
                        db.add(
                            SubscriptionPeriod(
                                id=new_id,
                                contract_id=contract_id,
                                mode=period.mode,
                                start_date=period.start_date,
                                end_date=period.end_date,
                                allowance=allowance(
                                    term, period.start_date, period.end_date
                                ),
                                actual=period.actual,
                                forecast=period.forecast,
                                details=period.details,
                                computed_at=period.computed_at,
                            )
                        )
            row.details = {**(row.details or {}), "superseded_by": contract_id}
        canonical_ids.append(contract_id)
    canonical = [db.get(SubscriptionContract, identity) for identity in canonical_ids]
    for term in canonical:
        overlaps = [
            other.id
            for other in canonical
            if other.id != term.id
            and parent_id(other) == parent_id(term)
            and other.currency == term.currency
            and other.start_date < term.end_date
            and term.start_date < other.end_date
        ]
        term.details = {
            **term.details,
            "grouping_review_required": bool(overlaps),
            "grouping_note": (
                "Overlapping dated terms lack a shared verified identity; kept separate for review."
                if overlaps
                else None
            ),
        }
    source_owners = {
        row.id: (row.details or {}).get("superseded_by") for row in candidates
    }
    for old in all_rows:
        if (old.details or {}).get("canonical_term") and old.id not in canonical_ids:
            owners = {
                source_owners.get(identity)
                for identity in old.details.get("source_line_ids", [])
            }
            if owners and None not in owners:
                old.details = {
                    **old.details,
                    "metadata_only": True,
                    "superseded_by": next(iter(owners)) if len(owners) == 1 else None,
                    "grouping_warning": "Replaced by terms with newer verified identities; original evidence retained.",
                }
    db.commit()
    return canonical_ids


def _save_line(db, line, row, contract_id):
    line.contract_id, line.source_contract_id = contract_id, row.id
    line.start_date, line.end_date = row.start_date, row.end_date
    line.total_value, line.currency, line.status = (
        row.total_value,
        row.currency,
        row.status,
    )
    line.details, line.computed_at = row.details or {}, row.computed_at
    db.add(line)

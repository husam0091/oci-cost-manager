"""Optional OCI discovery. Keep source failures independent and never infer money from SKU counts."""

from datetime import UTC, datetime
from services.event_logger import redact_sensitive
import oci

# Policy guidance is attached to the operation that failed, never inferred from a 404 alone.
POLICIES = {
    "oci:organizations": [
        "Allow group <group> to read organizations-subscriptions in tenancy",
        "Allow group <group> to read organizations-assigned-subscriptions in tenancy",
    ],
    "oci:onesubscription": [],
    "oci:osp": [],
    "oci:usage": ["Allow group <group> to read usage-report in tenancy"],
}


def _rows(data):
    return data if isinstance(data, list) else getattr(data, "items", []) or []


def discover(client, subscription_ids=None):
    """Return raw, paginated SDK evidence; normalize only explicit monetary fields later."""
    reports, contracts = {}, []

    def call(source, label, factory, method, **kwargs):
        key = f"{source}/{label}"
        try:
            sdk = factory(
                client.config,
                timeout=(3, 5),
                retry_strategy=oci.retry.NoneRetryStrategy(),
            )
            fn = getattr(sdk, method)
            # SDK list_subscriptions in Organizations has **kwargs only; tenancy is implicit.
            result, page = [], None
            while True:
                response = fn(**kwargs, **({"page": page} if page else {}))
                result.extend(
                    oci.util.to_dict(row)
                    for row in (
                        _rows(response.data)
                        if method.startswith("list_")
                        else [response.data]
                    )
                )
                page = response.headers.get("opc-next-page")
                if not page:
                    break
            reports[key] = {
                "status": "ok" if result else "empty",
                "count": len(result),
                "policies": POLICIES.get(source, []),
                "policy_note": (
                    "OneSubscription/OSP entitlement policies require confirmation with Oracle for this account; no unverified IAM statement is suggested."
                    if source in {"oci:onesubscription", "oci:osp"}
                    else None
                ),
            }
            return result
        except Exception as exc:
            status = getattr(exc, "status", None)
            reports[key] = {
                "status": (
                    "forbidden_or_not_found"
                    if status in (401, 403, 404)
                    else "unavailable"
                ),
                "http_status": status,
                "code": getattr(exc, "code", type(exc).__name__),
                "error": redact_sensitive(str(exc))[:4000],
                "policies": POLICIES.get(source, []),
                "policy_note": (
                    "OneSubscription/OSP entitlement policies require confirmation with Oracle for this account; no unverified IAM statement is suggested."
                    if source in {"oci:onesubscription", "oci:osp"}
                    else None
                ),
            }
            return []

    org = oci.tenant_manager_control_plane.SubscriptionClient
    owned = call("oci:organizations", "subscriptions", org, "list_subscriptions")
    assigned = call(
        "oci:organizations",
        "assigned",
        org,
        "list_assigned_subscriptions",
        compartment_id=client.tenancy_id,
    )
    for label, rows in (("owned", owned), ("assigned", assigned)):
        for row in rows:
            sid = row.get("id")
            if not sid:
                continue
            details = call(
                "oci:organizations",
                f"{label}:{sid}",
                org,
                "get_subscription" if label == "owned" else "get_assigned_subscription",
                **(
                    {"subscription_id": sid}
                    if label == "owned"
                    else {"assigned_subscription_id": sid}
                ),
            )
            # Get operations return an object, not a collection (handled below by call).
            for detail in details or [row]:
                contracts.append({**detail, "source": "oci:organizations"})

    identifiers = list(
        dict.fromkeys(
            str(row.get("subscription_number") or row.get("classic_subscription_id"))
            for row in contracts
            if row.get("subscription_number") or row.get("classic_subscription_id")
        )
    )
    identifiers = list(dict.fromkeys([*identifiers, *(subscription_ids or [])]))
    one = []
    for sid in identifiers:
        rows = call(
            "oci:onesubscription",
            f"subscriptions:{sid}",
            oci.onesubscription.SubscriptionClient,
            "list_subscriptions",
            compartment_id=client.tenancy_id,
            subscription_id=sid,
            is_commit_info_required=True,
        )
        one.extend({**row, "id": sid} for row in rows)
    if not identifiers:
        reports["oci:onesubscription/subscriptions"] = {
            "status": "needs_identifier",
            "error": "OneSubscription requires a subscription ID, plan number or buyer email. Organizations did not return one.",
            "policies": POLICIES["oci:onesubscription"],
        }
    for sub in one:
        sid = sub["id"]
        services = call(
            "oci:onesubscription",
            f"services:{sid}",
            oci.onesubscription.SubscribedServiceClient,
            "list_subscribed_services",
            compartment_id=client.tenancy_id,
            subscription_id=sid,
        )
        schedules = call(
            "oci:onesubscription",
            f"billing:{sid}",
            oci.onesubscription.BillingScheduleClient,
            "list_billing_schedules",
            compartment_id=client.tenancy_id,
            subscription_id=sid,
        )
        now = datetime.now(UTC)
        rated = call(
            "oci:onesubscription",
            f"rated:{sid}",
            oci.onesubscription.ComputedUsageClient,
            "list_aggregated_computed_usages",
            compartment_id=client.tenancy_id,
            subscription_id=sid,
            time_from=now.replace(day=1, hour=0, minute=0, second=0, microsecond=0),
            time_to=now,
            grouping="MONTHLY",
        )
        commitments = []
        for svc in services:
            if svc.get("id"):
                commitments.extend(
                    call(
                        "oci:onesubscription",
                        f"commitment:{svc['id']}",
                        oci.onesubscription.CommitmentClient,
                        "list_commitments",
                        compartment_id=client.tenancy_id,
                        subscribed_service_id=svc["id"],
                    )
                )
        contracts.append(
            {
                **sub,
                "id": sid,
                "source": "oci:onesubscription",
                "services": services,
                "commitments": commitments,
                "billing_schedule": schedules,
                "rated_usage": rated,
            }
        )
    # Reuse the existing fallback helper only when primary subscription discovery is empty.
    if not contracts:
        try:
            fallback = client.get_subscriptions()
            contracts.extend(
                {**row, "source": "oci:onesubscription", "legacy_fallback": True}
                for row in fallback
            )
            reports["oci:onesubscription/legacy-fallback"] = {
                "status": "ok" if fallback else "empty",
                "count": len(fallback),
            }
        except Exception as exc:
            reports["oci:onesubscription/legacy-fallback"] = {
                "status": "unavailable",
                "error": redact_sensitive(str(exc))[:4000],
                "policies": POLICIES["oci:onesubscription"] + POLICIES["oci:osp"],
            }
    return contracts, reports

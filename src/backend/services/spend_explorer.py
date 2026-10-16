"""Explain OCI-reported charges without estimating list prices or mixing currencies."""

from decimal import Decimal


def licensing_evidence(sku_name: str) -> dict:
    text = (sku_name or "").lower()
    if "byol" in text or "bring your own" in text:
        return {
            "model": "BYOL",
            "explanation": "SKU explicitly identifies BYOL. Existing license/support costs are outside this OCI charge.",
        }
    if "license included" in text or "license-included" in text:
        return {
            "model": "License included",
            "explanation": "SKU explicitly identifies an included software license. Do not add a second license estimate.",
        }
    if any(
        term in text
        for term in ("windows os", "windows server", "sql server", "microsoft sql")
    ):
        return {
            "model": "Metered software charge",
            "explanation": "Software-related billed SKU. Check the subscription or Marketplace agreement for PAYG terms; the SKU alone does not prove eligibility.",
        }
    return {
        "model": "Not determined",
        "explanation": "No explicit licensing model in this SKU. A zero or missing software charge does not prove BYOL.",
    }


def explain_spend(
    items: list[dict], resource_map: dict, *, service=None, resource_id=None
) -> dict:
    totals = {}
    lines = []
    for item in items:
        currency = item.get("currency") or "Unspecified"
        cost = Decimal(str(item.get("computed_amount") or 0))
        bucket = totals.setdefault(
            currency, {"charges": Decimal(0), "credits": Decimal(0), "net": Decimal(0)}
        )
        bucket["net"] += cost
        bucket["credits" if cost < 0 else "charges"] += cost
        rid = item.get("resource_id") or resource_id
        model = resource_map.get(rid)
        quantity = item.get("quantity")
        # Quantity is meaningful only when OCI grouped by unit. Never invent it.
        unit = item.get("unit")
        rate = (
            cost / Decimal(str(quantity))
            if unit and quantity and cost >= 0 and quantity > 0
            else None
        )
        lines.append(
            {
                "service": item.get("service") or service or "Not supplied by OCI",
                "resource_id": rid,
                "resource_name": (
                    model.name if model else rid or "Not attributed to a resource"
                ),
                "compartment_id": (
                    model.compartment_id if model else item.get("compartment_id")
                ),
                "region": model.region if model else item.get("region"),
                "sku_name": item.get("sku_name") or "Not supplied by OCI",
                "sku_part_number": item.get("sku_part_number"),
                "cost": float(cost),
                "currency": currency,
                "quantity": quantity if unit else None,
                "unit": unit,
                "effective_unit_cost": float(rate) if rate is not None else None,
                "charge_type": "Credit / adjustment" if cost < 0 else "Usage charge",
                "licensing": licensing_evidence(item.get("sku_name")),
            }
        )
    lines.sort(
        key=lambda row: (
            row["currency"],
            -abs(row["cost"]),
            row["resource_name"],
            row["sku_name"],
        )
    )
    return {
        "services": sorted(
            {
                line["service"]
                for line in lines
                if line["service"] != "Not supplied by OCI"
            }
        ),
        "items": lines,
        "totals": [
            {
                "currency": currency,
                **{key: float(value) for key, value in amounts.items()},
            }
            for currency, amounts in sorted(totals.items())
        ],
    }

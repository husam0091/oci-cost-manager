from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from api.routes import billing, data
from core.database import Base, get_db
from core.models import Resource
from core.rbac import Principal
from services.cost_calculator import CostCalculatorService
from services.spend_explorer import explain_spend, licensing_evidence


def test_credits_currency_and_missing_quantity_are_preserved():
    result = explain_spend(
        [
            {
                "computed_amount": 100,
                "currency": "USD",
                "sku_name": "Windows OS",
                "quantity": 10,
                "unit": "OCPU hour",
            },
            {"computed_amount": -5, "currency": "USD", "sku_name": "Credit"},
            {"computed_amount": 200, "currency": "SAR", "quantity": 50},
        ],
        {},
    )
    assert result["totals"] == [
        dict(currency="SAR", charges=200, credits=0, net=200),
        dict(currency="USD", charges=100, credits=-5, net=95),
    ]
    win = next(r for r in result["items"] if r["sku_name"] == "Windows OS")
    assert win["effective_unit_cost"] == 10
    sar = next(r for r in result["items"] if r["currency"] == "SAR")
    assert sar["quantity"] is None and sar["effective_unit_cost"] is None
    assert sar["resource_name"] == "Not attributed to a resource"


@pytest.mark.parametrize(
    "sku,expected",
    [
        ("Database BYOL", "BYOL"),
        ("Database License Included", "License included"),
        ("SQL Server Standard", "Metered software charge"),
        ("Compute", "Not determined"),
    ],
)
def test_licensing_requires_billing_evidence(sku, expected):
    assert licensing_evidence(sku)["model"] == expected


def test_usage_query_preserves_zero_and_uses_computed_quantity():
    captured = []
    row = SimpleNamespace(
        computed_amount=0,
        cost=999,
        computed_quantity=7,
        quantity=888,
        unit="hour",
        currency="USD",
    )
    calc = CostCalculatorService.__new__(CostCalculatorService)
    calc.oci_client = SimpleNamespace(
        tenancy_id="tenancy",
        usage_client=SimpleNamespace(
            request_summarized_usages=lambda req: captured.append(req)
            or SimpleNamespace(data=SimpleNamespace(items=[row]))
        ),
    )
    kwargs = dict(
        start_date=datetime(2026, 1, 1, tzinfo=UTC),
        end_date=datetime(2026, 2, 1, tzinfo=UTC),
    )
    result = calc.get_usage_summary(
        **kwargs, group_by=["skuName", "unit"], service="Compute", resource_id="r1"
    )
    assert captured[0].group_by == ["skuName", "unit", "currency"]
    assert {d.key: d.value for d in captured[0].filter.dimensions} == {
        "service": "Compute",
        "resourceId": "r1",
    }
    assert result[0]["computed_amount"] == 0
    assert result[0]["quantity"] == 7
    assert calc.get_usage_summary(**kwargs, group_by=["service"])[0]["quantity"] is None
    with pytest.raises(ValueError):
        calc.get_usage_summary(
            **kwargs, group_by=["service", "skuName", "unit", "resourceId"]
        )


@pytest.fixture
def inventory():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add_all(
            [
                Resource(
                    ocid="r1",
                    name="same",
                    type="compute",
                    region="me-jeddah-1",
                    compartment_id="c1",
                    status="RUNNING",
                    details={"env": "dev", "team": "A", "app": "web"},
                ),
                Resource(
                    ocid="r2",
                    name="same",
                    type="compute",
                    region="me-jeddah-1",
                    compartment_id="c1",
                    status="RUNNING",
                    details={"env": "prod", "team": "B", "app": "web"},
                ),
                Resource(
                    ocid="r3",
                    name="percent%host",
                    type="compute",
                    region="me-riyadh-1",
                    compartment_id="c2",
                    status="STOPPED",
                    details={},
                ),
            ]
        )
        db.commit()
        app = FastAPI()
        app.include_router(data.router, prefix="/data")
        app.include_router(billing.router, prefix="/billing")
        app.dependency_overrides[get_db] = lambda: db
        yield TestClient(app), db
    engine.dispose()


def test_allocation_filters_before_pagination_and_literal_search(inventory):
    client, _ = inventory
    payload = client.get("/data/resources?env=prod&limit=1").json()
    assert [r["id"] for r in payload["data"]] == ["r2"]
    assert payload["meta"]["total"] == 1
    assert payload["meta"]["has_more"] is False
    first = client.get("/data/resources?limit=1").json()
    second = client.get("/data/resources?limit=1&offset=1").json()
    assert first["data"][0]["id"] == "r3"  # name ordering
    assert second["data"][0]["id"] == "r1"
    assert first["meta"]["has_more"] is True
    assert client.get("/data/resources?search=%25").json()["meta"]["total"] == 1
    assert (
        client.get("/data/resources?unowned_only=true&limit=1").json()["data"][0]["id"]
        == "r3"
    )
    assert client.get("/data/resources?status=STOPPED").json()["meta"]["total"] == 1
    assert client.get("/data/resources?sort_by=invalid").status_code == 422


def test_billed_spend_auth_scope_pagination_and_cache(inventory, monkeypatch):
    client, _ = inventory
    assert (
        client.get(
            "/billing/spend?start_date=2026-01-01&end_date=2026-01-31"
        ).status_code
        == 401
    )
    principal = Principal("admin", "admin", [], [], [], [])
    monkeypatch.setattr(billing, "resolve_principal", lambda *a, **kw: principal)
    calls = []

    def usage(**kwargs):
        calls.append(kwargs)
        return [
            dict(
                resource_id="r1",
                service="Compute",
                sku_name="Compute",
                computed_amount=100,
                currency="USD",
            ),
            dict(
                resource_id="r2",
                service="Compute",
                sku_name="Windows OS",
                computed_amount=50,
                currency="USD",
            ),
            dict(
                service="Storage",
                sku_name="Unattributed",
                computed_amount=20,
                currency="USD",
            ),
        ]

    monkeypatch.setattr(
        billing, "get_cost_calculator", lambda: SimpleNamespace(get_usage_summary=usage)
    )
    url = "/billing/spend?start_date=2026-01-01&end_date=2026-01-31&limit=1"
    first = client.get(url).json()
    assert first["data"]["totals"][0]["net"] == 170
    assert first["meta"]["has_more"] is True
    assert first["meta"]["cached"] is False
    assert client.get(url + "&offset=1").json()["meta"]["cached"] is True
    assert len(calls) == 1
    assert calls[0]["group_by"] == ["service", "skuName", "resourceId"]
    principal = Principal("analyst", "finops", ["B"], [], [], [])
    scoped = client.get(url).json()
    assert scoped["data"]["totals"][0]["net"] == 50
    assert scoped["data"]["scope_limited"] is True
    assert len(calls) == 2
    client.get(url + "&resource_id=r2")
    assert calls[-1]["group_by"] == ["skuName", "skuPartNumber", "unit"]
    assert client.get(url + "&refresh=true").json()["meta"]["cached"] is False
    assert (
        client.get(
            "/billing/spend?start_date=2024-01-01&end_date=2026-01-31"
        ).status_code
        == 422
    )


def test_billing_errors_never_substitute_fake_zero(inventory, monkeypatch):
    client, _ = inventory
    monkeypatch.setattr(
        billing,
        "resolve_principal",
        lambda *a, **kw: Principal("admin", "admin", [], [], [], []),
    )

    def fail():
        raise RuntimeError("private credential path")

    monkeypatch.setattr(billing, "get_cost_calculator", fail)
    response = client.get("/billing/spend?start_date=2026-01-01&end_date=2026-01-31")
    assert response.status_code == 503
    assert "private credential" not in response.text

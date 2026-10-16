"""Accounting regression fixtures and API contract coverage for Interface 2.3."""

from datetime import UTC, date, datetime
from decimal import Decimal
from types import SimpleNamespace as NS
import json
import time
import threading
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from core.database import Base, get_db
from core.models import SubscriptionContract, SubscriptionPeriod, Setting
from core.rbac import Principal
from api.routes import commitments, billing
from services.commitments import month_at, windows, allowance, normalize, sync
from services.cost_calculator import CostCalculatorService


@pytest.mark.parametrize(
    "anchor,offset,expected",
    [
        (date(2026, 1, 31), 1, date(2026, 2, 28)),
        (date(2026, 1, 31), 2, date(2026, 3, 31)),
        (date(2024, 1, 31), 1, date(2024, 2, 29)),
        (date(2024, 2, 29), 12, date(2025, 2, 28)),
        (date(2026, 12, 15), 1, date(2027, 1, 15)),
    ],
)
def test_anniversary_anchor_does_not_drift(anchor, offset, expected):
    assert month_at(anchor, offset) == expected


def test_calendar_proration_and_anniversary():
    contract = NS(
        start_date=date(2026, 3, 15),
        end_date=date(2027, 3, 15),
        term_months=12,
        total_value=Decimal(12000),
    )
    assert sum(
        (
            allowance(contract, a, b)
            for a, b in windows(contract.start_date, contract.end_date, "calendar")
        ),
        Decimal(0),
    ) == Decimal(12000)
    assert (date(2026, 10, 15), date(2026, 11, 15)) in list(
        windows(contract.start_date, contract.end_date)
    )
    assert allowance(contract, date(2026, 3, 15), date(2026, 4, 15)) == 1000
    assert (
        allowance(contract, date(2026, 3, 15), date(2026, 4, 1))
        == Decimal(1000) * 17 / 31
    )


def test_partial_last_month():
    contract = NS(
        start_date=date(2024, 1, 31),
        end_date=date(2024, 3, 15),
        term_months=2,
        total_value=Decimal(200),
    )
    assert (
        allowance(contract, date(2024, 2, 29), date(2024, 3, 15))
        == Decimal(100) * 15 / 31
    )


@pytest.mark.parametrize(
    "quantity,raises", [(0, False), ("0", False), (1, True), (-1, True), (None, True)]
)
def test_january_null_amount_fixture(quantity, raises):
    row = NS(
        service="Object Storage",
        sku_name="Object Storage - Requests",
        computed_amount=None,
        computed_quantity=quantity,
        currency=" ",
    )
    calculator = CostCalculatorService.__new__(CostCalculatorService)
    calculator.oci_client = NS(
        tenancy_id="tenancy",
        usage_client=NS(
            request_summarized_usages=lambda *_a, **_k: NS(data=NS(items=[row]))
        ),
    )
    call = lambda: calculator.get_usage_summary(
        datetime(2026, 1, 1, tzinfo=UTC), datetime(2026, 2, 1, tzinfo=UTC)
    )
    if raises:
        with pytest.raises(ValueError):
            call()
    else:
        assert call()[0]["computed_amount"] == 0


def test_usage_pagination_preserves_credits_and_zero():
    calls = []

    def request(details, **kwargs):
        calls.append(kwargs)
        return NS(
            data=NS(items=[NS(computed_amount=-2 if kwargs else 0, currency="USD")]),
            headers={} if kwargs else {"opc-next-page": "next"},
        )

    calculator = CostCalculatorService.__new__(CostCalculatorService)
    calculator.oci_client = NS(
        tenancy_id="tenancy", usage_client=NS(request_summarized_usages=request)
    )
    assert [
        r["computed_amount"]
        for r in calculator.get_usage_summary(
            datetime(2026, 1, 1, tzinfo=UTC), datetime(2026, 2, 1, tzinfo=UTC)
        )
    ] == [0, -2]
    assert calls == [{}, {"page": "next"}]


def test_normalization_never_prices_sku_quantity():
    now = datetime.now(UTC)
    raw = dict(
        id="org1",
        source="oci:organizations",
        start_date="2026-03-15",
        end_date="2027-03-15",
        currency_code="USD",
        skus=[{"quantity": 90000}],
    )
    assert normalize(raw, now)["total_value"] is None
    assert normalize({**raw, "total_value": "12000"}, now)["total_value"] == 12000
    assert normalize({**raw, "currency_code": None}, now) is None


@pytest.fixture
def api(monkeypatch, tmp_path):
    from core import cache

    monkeypatch.setattr(cache, "CACHE_DIR", tmp_path)
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        app = FastAPI()
        app.include_router(commitments.router, prefix="/subscriptions")
        app.include_router(billing.router, prefix="/billing")

        @app.get("/health")
        async def health():
            return {"ok": True}

        app.dependency_overrides[get_db] = lambda: db
        principal = Principal("admin", "admin", [], [], [], [])
        monkeypatch.setattr(
            commitments, "resolve_principal", lambda *_a, **_k: principal
        )
        monkeypatch.setattr(billing, "resolve_principal", lambda *_a, **_k: principal)
        yield TestClient(app), db, principal
    engine.dispose()


def test_api_manual_validation_and_no_fake_zero(api):
    client, db, _ = api
    payload = dict(
        name="Annual credits",
        total_value="12000",
        currency="USD",
        start_date="2026-03-15",
        end_date="2027-03-15",
        term_months=12,
    )
    response = client.post("/subscriptions/contracts", json=payload)
    assert response.status_code == 201
    contract = response.json()["data"]
    assert contract["source"] == "manual"
    assert (
        client.post(
            "/subscriptions/contracts", json={**payload, "currency": "usd"}
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/subscriptions/contracts", json={**payload, "end_date": "2027-04-01"}
        ).status_code
        == 422
    )
    data = client.get(
        "/subscriptions/overview", params={"contract_id": contract["id"]}
    ).json()["data"]
    assert data["consumed_to_date"] is None
    assert data["meta"]["payg_rate_spend"] is None
    assert len(json.dumps(data)) < 300000


def test_scoped_principal_and_feature_flag(api):
    client, db, principal = api
    principal.role = "viewer"
    principal.allowed_teams = ["A"]
    assert client.get("/subscriptions/contracts").status_code == 403
    principal.allowed_teams = []
    assert client.post("/subscriptions/sync").status_code == 403
    db.add(Setting(id=1, commitments_enabled=False))
    db.commit()
    assert client.get("/subscriptions/contracts").status_code == 404


def test_currency_separation_region_and_missing_period(api):
    client, db, _ = api
    now = datetime.now(UTC)
    today = now.date()
    start = today.replace(day=1)
    end = month_at(start, 1)
    c = SubscriptionContract(
        id="c",
        source="manual",
        name="credits",
        start_date=start,
        end_date=month_at(start, 12),
        term_months=12,
        total_value=1200,
        currency="USD",
        computed_at=now,
        details={},
    )
    db.add(c)
    db.add(
        SubscriptionPeriod(
            id="p",
            contract_id="c",
            mode="calendar",
            start_date=start,
            end_date=end,
            allowance=100,
            actual=999,
            computed_at=now,
            details={
                "complete": True,
                "elapsed_days": 10,
                "facts": [
                    {
                        "currency": "USD",
                        "region": "jeddah",
                        "service": "Compute",
                        "compartment": "c1",
                        "amount": "80",
                    },
                    {
                        "currency": "USD",
                        "region": "jeddah",
                        "service": "Compute",
                        "compartment": "c1",
                        "amount": "-10",
                    },
                    {
                        "currency": "EUR",
                        "region": "jeddah",
                        "service": "Compute",
                        "compartment": "c1",
                        "amount": "500",
                    },
                    {
                        "currency": "USD",
                        "region": "riyadh",
                        "service": "Storage",
                        "compartment": "c2",
                        "amount": "20",
                    },
                ],
            },
        )
    )
    db.commit()
    result = client.get(
        "/subscriptions/overview?contract_id=c&mode=calendar&region=jeddah"
    ).json()["data"]
    assert result["consumed_to_date"] == 70
    assert result["periods"][0]["credits"] == -10
    assert result["periods"][0]["allowance"] == 100
    breakdown = client.get("/subscriptions/breakdown?period=p&region=jeddah").json()
    assert breakdown["data"][0]["actual"] == 70
    assert client.get("/subscriptions/breakdown?period=missing").status_code == 404


def test_billing_parse_error_distinct_and_logged(api, monkeypatch, caplog):
    client, _, _ = api

    def fail(**kwargs):
        raise ValueError("fixture missing amount")

    monkeypatch.setattr(
        billing, "get_cost_calculator", lambda: NS(get_usage_summary=fail)
    )
    response = client.get("/billing/spend?start_date=2026-01-01&end_date=2026-01-31")
    assert response.status_code == 502
    assert response.json()["detail"]["code"] == "OCI_BILLING_PARSE_ERROR"
    assert response.json()["detail"]["correlation_id"] in caplog.text


def test_cold_endpoint_keeps_health_responsive(api, monkeypatch):
    import asyncio
    import httpx

    client, _, _ = api
    original = commitments.view

    def slow(*args, **kwargs):
        time.sleep(0.4)
        return original(*args, **kwargs)

    monkeypatch.setattr(commitments, "view", slow)

    async def probe():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=client.app), base_url="http://test"
        ) as ac:
            running = asyncio.create_task(ac.get("/subscriptions/overview"))
            measurements = []
            last = time.perf_counter()
            for _ in range(20):
                await asyncio.sleep(0.02)
                start = time.perf_counter()
                assert (await ac.get("/health")).status_code == 200
                finish = time.perf_counter()
                measurements.append(max(finish - start, finish - last - 0.02))
                last = finish
            assert (await running).status_code == 200
            assert sorted(measurements)[int(len(measurements) * 0.95)] < 0.2

    asyncio.run(probe())


def test_sync_manual_survives_discovery_failure_and_keeps_currency(api, monkeypatch):
    from services import commitments as service

    client, db, _ = api
    today = datetime.now(UTC).date()
    start = today.replace(day=1)
    db.add(
        SubscriptionContract(
            id="manual",
            source="manual",
            name="Annual",
            start_date=start,
            end_date=month_at(start, 12),
            currency="USD",
            total_value=1200,
            term_months=12,
            computed_at=datetime.now(UTC),
            details={},
        )
    )
    db.commit()
    monkeypatch.setattr(service, "get_oci_client", lambda: NS())
    monkeypatch.setattr(
        service,
        "discover",
        lambda *a, **k: (
            [],
            {
                "oci:organizations": {
                    "status": "forbidden_or_not_found",
                    "error": "NotAuthorizedOrNotFound",
                    "policies": ["required-policy"],
                }
            },
        ),
    )

    def usage(*a, **kwargs):
        if kwargs.get("query_type"):
            raise RuntimeError("credit source independently unavailable")
        return [
            dict(
                time_usage_started=start.isoformat(),
                currency="USD",
                service="Compute",
                computed_amount=25,
            ),
            dict(
                time_usage_started=start.isoformat(),
                currency="EUR",
                service="Compute",
                computed_amount=1000,
            ),
        ]

    monkeypatch.setattr(
        service, "get_cost_calculator", lambda: NS(get_usage_summary=usage)
    )
    result = sync(db)
    assert result["status"] == "partial"
    assert db.query(SubscriptionPeriod).count() == 2
    response = client.get("/subscriptions/overview?contract_id=manual").json()["data"]
    assert response["consumed_to_date"] == 25
    assert (
        response["diagnostics"]["sources"]["oci:organizations"]["error"]
        == "NotAuthorizedOrNotFound"
    )


def test_source_discovery_uses_real_sdk_signatures_and_independent_results(monkeypatch):
    import oci
    from services.subscription_sources import discover

    calls = []

    class Org:
        def __init__(self, *a, **k):
            pass

        def list_subscriptions(self, **kwargs):
            assert "compartment_id" not in kwargs
            return NS(data=NS(items=[{"id": "org"}]), headers={})

        def list_assigned_subscriptions(self, compartment_id, **kwargs):
            raise oci.exceptions.ServiceError(
                404, "NotAuthorizedOrNotFound", {}, "fixture forbidden"
            )

        def get_subscription(self, subscription_id, **kwargs):
            return NS(
                data={
                    "id": "org",
                    "subscription_number": "number",
                    "currency_code": "USD",
                },
                headers={},
            )

    class One:
        def __init__(self, *a, **k):
            pass

        def list_subscriptions(self, compartment_id, subscription_id, **kwargs):
            calls.append(subscription_id)
            return NS(
                data=[
                    {
                        "time_start": "2026-01-01",
                        "time_end": "2027-01-01",
                        "currency": {"iso_code": "USD"},
                        "subscribed_services": [
                            {
                                "id": "svc",
                                "total_value": "1200",
                                "time_start": "2026-01-01",
                                "time_end": "2027-01-01",
                            }
                        ],
                    }
                ],
                headers={},
            )

        def list_subscribed_services(self, compartment_id, subscription_id, **kwargs):
            return NS(data=[{"id": "svc"}], headers={})

        def list_commitments(self, subscribed_service_id, compartment_id, **kwargs):
            return NS(data=[{"id": "commit"}], headers={})

        def list_billing_schedules(self, compartment_id, subscription_id, **kwargs):
            return NS(data=[], headers={})

        def list_aggregated_computed_usages(
            self, compartment_id, subscription_id, time_from, time_to, **kwargs
        ):
            return NS(data=[], headers={})

    monkeypatch.setattr(oci.tenant_manager_control_plane, "SubscriptionClient", Org)
    for name in [
        "SubscriptionClient",
        "SubscribedServiceClient",
        "CommitmentClient",
        "BillingScheduleClient",
        "ComputedUsageClient",
    ]:
        monkeypatch.setattr(oci.onesubscription, name, One)
    raw, reports = discover(NS(config={}, tenancy_id="tenancy"))
    assert calls == ["number"]
    assert reports["oci:organizations/assigned"]["status"] == "forbidden_or_not_found"
    assert reports["oci:onesubscription/commitment:svc"]["count"] == 1
    normalized = normalize(
        next(row for row in raw if row["source"] == "oci:onesubscription"),
        datetime.now(UTC),
    )
    assert normalized["total_value"] == 1200


def test_exports_csv_and_xlsx(api, monkeypatch, tmp_path):
    from core import config

    client, db, _ = api
    now = datetime.now(UTC)
    today = now.date()
    db.add(
        SubscriptionContract(
            id="export",
            source="manual",
            name="Annual",
            start_date=today,
            end_date=month_at(today, 12),
            currency="USD",
            total_value=1200,
            term_months=12,
            computed_at=now,
            details={},
        )
    )
    db.commit()
    monkeypatch.setattr(config, "get_settings", lambda: NS(export_dir=str(tmp_path)))
    csv = client.get("/subscriptions/export?contract_id=export&format=csv")
    assert csv.status_code == 200 and "allowance_estimate" in csv.text
    xlsx = client.get("/subscriptions/export?contract_id=export&format=xlsx")
    assert xlsx.status_code == 200 and xlsx.content.startswith(b"PK")


def test_migration_upgrade_is_idempotent_and_creates_tables():
    import importlib.util
    from pathlib import Path
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from sqlalchemy import inspect, text

    path = Path(__file__).parents[1] / "alembic/versions/20261017_01_commitments.py"
    spec = importlib.util.spec_from_file_location("commitment_migration", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        Setting.__table__.create(connection)
        connection.execute(text("ALTER TABLE settings DROP COLUMN commitments_enabled"))
        module.op = Operations(MigrationContext.configure(connection))
        module.upgrade()
        module.upgrade()
        assert {
            "subscription_contracts",
            "subscription_periods",
            "subscription_sync_runs",
        } <= set(inspect(connection).get_table_names())
        assert "commitments_enabled" in {
            row["name"] for row in inspect(connection).get_columns("settings")
        }
        assert (
            inspect(connection).get_unique_constraints("subscription_periods")[0][
                "name"
            ]
            == "uq_subscription_period"
        )
    engine.dispose()


def test_contract_renewals_do_not_reuse_previous_term_periods():
    raw = dict(
        id="same-subscription",
        source="oci:onesubscription",
        currency_code="USD",
        total_value="12000",
        time_start="2026-03-15",
        time_end="2027-03-15",
    )
    first = normalize(raw, datetime.now(UTC))
    renewed = normalize(
        {**raw, "time_start": "2027-03-15", "time_end": "2028-03-15"}, datetime.now(UTC)
    )
    assert first["id"] != renewed["id"]
    assert first["term_months"] == renewed["term_months"] == 12

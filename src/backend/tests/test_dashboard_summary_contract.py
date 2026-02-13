from datetime import UTC, datetime

from fastapi.testclient import TestClient

from main import app
from api.routes import dashboard


client = TestClient(app)


class RecordingCalculator:
    def __init__(self):
        self.by_service_calls = []
        self.by_resource_calls = []

    def get_costs_by_service(self, start, end):
        self.by_service_calls.append((start, end))
        if len(self.by_service_calls) == 1:
            return {"Compute": 200.0, "Storage": 100.0}
        return {"Compute": 100.0, "Storage": 100.0}

    def get_costs_by_resource(self, start, end, include_skus=True, compartment_id=None):
        self.by_resource_calls.append((start, end, include_skus))
        if len(self.by_resource_calls) == 1:
            return [
                {
                    "resource_id": "r1",
                    "total_cost": 200.0,
                    "skus": [{"sku_name": "Windows OS", "cost": 200.0, "quantity": 1}],
                },
                {
                    "resource_id": "r2",
                    "total_cost": 100.0,
                    "skus": [{"sku_name": "Block Volume - Backup", "cost": 100.0, "quantity": 3}],
                },
            ]
        return [
            {
                "resource_id": "r1",
                "total_cost": 150.0,
                "skus": [{"sku_name": "Windows OS", "cost": 150.0, "quantity": 1}],
            },
            {
                "resource_id": "r2",
                "total_cost": 50.0,
                "skus": [{"sku_name": "Block Volume - Backup", "cost": 50.0, "quantity": 1}],
            },
        ]


class EmptyCalculator:
    def get_costs_by_service(self, start, end):
        return {}

    def get_costs_by_resource(self, start, end, include_skus=True, compartment_id=None):
        return []


class SpotlightCalculator:
    def get_costs_by_service(self, start, end):
        return {"Compute": 300.0}

    def get_costs_by_resource(self, start, end, include_skus=True, compartment_id=None):
        if start.month == 1:
            return [
                {"resource_id": "r-foo", "compartment_id": "foo", "total_cost": 120.0, "skus": [{"sku_name": "Compute VM", "cost": 120.0}]},
                {"resource_id": "r-foo-child", "compartment_id": "foo-child", "total_cost": 80.0, "skus": [{"sku_name": "Block Volume", "cost": 80.0}]},
                {"resource_id": "r-ad1", "compartment_id": "ad1", "total_cost": 50.0, "skus": [{"sku_name": "Compute VM", "cost": 50.0}]},
            ]
        return [
            {"resource_id": "r-foo", "compartment_id": "foo", "total_cost": 100.0, "skus": [{"sku_name": "Compute VM", "cost": 100.0}]},
            {"resource_id": "r-foo-child", "compartment_id": "foo-child", "total_cost": 60.0, "skus": [{"sku_name": "Block Volume", "cost": 60.0}]},
            {"resource_id": "r-ad1", "compartment_id": "ad1", "total_cost": 40.0, "skus": [{"sku_name": "Compute VM", "cost": 40.0}]},
        ]


class _Q:
    def __init__(self, rows):
        self.rows = rows

    def filter(self, *_args, **_kwargs):
        return self

    def order_by(self, *_args, **_kwargs):
        return self

    def all(self):
        return self.rows

    def first(self):
        return self.rows[0] if self.rows else None

    def one_or_none(self):
        return self.rows[0] if self.rows else None


class _FakeSetting:
    id = 1
    important_compartments = ["foo"]
    important_compartment_ids = ["foo"]
    important_include_children = True


class _FakeComp:
    def __init__(self, cid, name, parent_id=None):
        self.id = cid
        self.name = name
        self.parent_id = parent_id


class _FakeResource:
    def __init__(self, ocid, compartment_id):
        self.ocid = ocid
        self.compartment_id = compartment_id
        self.type = "compute.instance"
        self.name = ocid
        self.details = {}


class SpotlightDB:
    def query(self, model):
        name = getattr(model, "__name__", "")
        if name == "Setting":
            return _Q([_FakeSetting()])
        if name == "Compartment":
            return _Q([_FakeComp("foo", "foo"), _FakeComp("foo-child", "foo-child", "foo"), _FakeComp("ad1", "ad1")])
        if name == "Resource":
            return _Q([
                _FakeResource("r-foo", "foo"),
                _FakeResource("r-foo-child", "foo-child"),
                _FakeResource("r-ad1", "ad1"),
            ])
        return _Q([])


def test_core_business_spotlight_child_inclusion_and_totals(monkeypatch):
    monkeypatch.setattr(dashboard, "get_cost_calculator", lambda: SpotlightCalculator())
    app.dependency_overrides[dashboard.get_db] = lambda: SpotlightDB()
    try:
        response = client.get("/api/v1/dashboard/summary?start_date=2026-01-01&end_date=2026-01-31")
        assert response.status_code == 200
        spotlight = response.json()["data"]["core_business_spotlight"]
        assert len(spotlight) == 1
        item = spotlight[0]
        assert item["compartment_id"] == "foo"
        assert item["include_children"] is True
        # includes foo + foo-child only for selected spotlight
        assert item["totals"]["current"] == 200.0
        assert item["totals"]["previous"] == 160.0
        assert item["totals"]["delta_abs"] == 40.0
        assert item["totals"]["delta_pct"] == 25.0
    finally:
        app.dependency_overrides.pop(dashboard.get_db, None)

def test_dashboard_summary_previous_period_and_inclusive_end(monkeypatch):
    calc = RecordingCalculator()
    monkeypatch.setattr(dashboard, "get_cost_calculator", lambda: calc)

    response = client.get("/api/v1/dashboard/summary?start_date=2026-01-01&end_date=2026-01-31")
    assert response.status_code == 200

    first_start, first_end = calc.by_service_calls[0]
    second_start, second_end = calc.by_service_calls[1]
    assert first_start == datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
    assert first_end == datetime(2026, 2, 1, 0, 0, tzinfo=UTC)  # inclusive end_date -> exclusive +1 day
    assert second_start == datetime(2025, 12, 1, 0, 0, tzinfo=UTC)
    assert second_end == datetime(2026, 1, 1, 0, 0, tzinfo=UTC)

    payload = response.json()["data"]
    assert payload["period"]["days"] == 31


def test_dashboard_summary_delta_math(monkeypatch):
    monkeypatch.setattr(dashboard, "get_cost_calculator", lambda: RecordingCalculator())
    response = client.get("/api/v1/dashboard/summary?start_date=2026-01-01&end_date=2026-01-31")
    assert response.status_code == 200
    totals = response.json()["data"]["totals"]
    assert totals["current"] == 300.0
    assert totals["previous"] == 200.0
    assert totals["delta_abs"] == 100.0
    assert totals["delta_pct"] == 50.0


def test_dashboard_summary_empty_period_returns_zeroes(monkeypatch):
    monkeypatch.setattr(dashboard, "get_cost_calculator", lambda: EmptyCalculator())
    response = client.get("/api/v1/dashboard/summary?start_date=2026-01-01&end_date=2026-01-31")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["totals"] == {"current": 0.0, "previous": 0.0, "delta_abs": 0.0, "delta_pct": 0.0}
    assert data["top_driver"]["group"] == "No data"
    assert data["biggest_mover"]["entity_name"] == "No data"
    assert data["storage_backup"]["unattached_volumes"]["count"] == 0
    assert data["mapping_health"]["unallocated_pct"] == 0.0


def test_dashboard_summary_schema_stability(monkeypatch):
    monkeypatch.setattr(dashboard, "get_cost_calculator", lambda: RecordingCalculator())
    response = client.get("/api/v1/dashboard/summary?start_date=2026-01-01&end_date=2026-01-31")
    assert response.status_code == 200
    payload = response.json()
    assert set(payload.keys()) == {"success", "data"}
    assert set(payload["data"].keys()) == {
        "period",
        "totals",
        "top_driver",
        "biggest_mover",
        "license_spotlight",
        "storage_backup",
        "mapping_health",
        "freshness",
        "core_business_spotlight",
        "savings_opportunities",
        "budget_health",
        "executive_signals",
    }
    assert set(payload["data"]["period"].keys()) == {"start_date", "end_date", "days"}
    assert set(payload["data"]["totals"].keys()) == {"current", "previous", "delta_abs", "delta_pct"}
    assert set(payload["data"]["top_driver"].keys()) == {"group", "current", "previous", "share_pct", "delta_abs", "delta_pct"}
    assert set(payload["data"]["biggest_mover"].keys()) == {"entity_type", "entity_name", "delta_abs", "delta_pct"}
    assert set(payload["data"]["license_spotlight"].keys()) == {"windows", "sql_server", "oracle_os"}
    assert set(payload["data"]["storage_backup"].keys()) == {"unattached_volumes", "backups"}
    assert set(payload["data"]["mapping_health"].keys()) == {"unallocated_pct", "low_confidence_count"}
    assert set(payload["data"]["freshness"].keys()) == {"last_scan_at", "last_cost_refresh_at"}
    assert isinstance(payload["data"]["core_business_spotlight"], list)
    assert set(payload["data"]["savings_opportunities"].keys()) == {"potential_savings_monthly", "high_confidence_savings", "recommendation_count"}
    assert set(payload["data"]["budget_health"].keys()) == {"total_budgets", "budgets_at_risk", "budgets_breached", "highest_utilization_budget"}
    assert set(payload["data"]["executive_signals"].keys()) == {
        "run_rate_vs_budget",
        "forecasted_month_end_spend",
        "top_risk_budget",
        "top_cost_driver_this_month",
    }


def test_descendants_includes_children():
    class C:
        def __init__(self, cid, parent):
            self.id = cid
            self.parent_id = parent

    tree = [
        C("root", None),
        C("foo", "root"),
        C("foo-child", "foo"),
        C("foo-grandchild", "foo-child"),
        C("ad1", "root"),
    ]
    got = dashboard._descendants({"foo"}, tree)
    assert got == {"foo", "foo-child", "foo-grandchild"}

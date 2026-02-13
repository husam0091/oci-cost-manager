from datetime import UTC, datetime

from fastapi.testclient import TestClient

from main import app
from api.routes import costs


client = TestClient(app)


class FakeCalcBreakdown:
    def __init__(self):
        self.service_calls = []

    def get_costs_by_service(self, start, end):
        self.service_calls.append((start, end))
        if len(self.service_calls) == 1:
            return {
                "Compute": 120.0,
                "Storage": 80.0,
                "Network": 40.0,
                "DB": 20.0,
            }
        return {
            "Compute": 100.0,
            "Storage": 90.0,
            "Network": 30.0,
            "DB": 10.0,
        }

    def get_costs_by_resource(self, start, end, include_skus=False, compartment_id=None):
        return []


class FakeCalcBreakdownMany:
    def get_costs_by_service(self, start, end):
        return {
            "A": 100.0,
            "B": 90.0,
            "C": 80.0,
            "D": 70.0,
            "E": 60.0,
            "F": 50.0,
            "G": 40.0,
            "H": 30.0,
            "I": 20.0,
            "J": 10.0,
        }

    def get_costs_by_resource(self, start, end, include_skus=False, compartment_id=None):
        return []


class FakeCalcEmpty:
    def get_costs_by_service(self, start, end):
        return {}

    def get_costs_by_resource(self, start, end, include_skus=False, compartment_id=None):
        return []


class FakeCalcMovers:
    def __init__(self):
        self.service_calls = []

    def get_costs_by_service(self, start, end):
        self.service_calls.append((start, end))
        if len(self.service_calls) == 1:
            return {"Compute": 200.0, "Storage": 100.0, "Network": 50.0}
        return {"Compute": 100.0, "Storage": 120.0, "Network": 50.0}

    def get_costs_by_resource(self, start, end, include_skus=False, compartment_id=None):
        if len(self.service_calls) == 0:
            return [
                {"resource_id": "ocid1.instance.oc1..aaaaaaaaaaaaaaaa", "total_cost": 300.0, "compartment_name": "Finance"},
                {"resource_id": "ocid1.instance.oc1..bbbbbbbbbbbbbbbb", "total_cost": 50.0, "compartment_name": "IT"},
            ]
        return [
            {"resource_id": "ocid1.instance.oc1..aaaaaaaaaaaaaaaa", "total_cost": 200.0, "compartment_name": "Finance"},
            {"resource_id": "ocid1.instance.oc1..bbbbbbbbbbbbbbbb", "total_cost": 20.0, "compartment_name": "IT"},
        ]


class FakeResource:
    def __init__(self, ocid, name=None, rtype=None, compartment_id=None, details=None):
        self.ocid = ocid
        self.name = name
        self.type = rtype
        self.compartment_id = compartment_id
        self.details = details or {}


class FakeQuery:
    def __init__(self, items):
        self._items = items

    def filter(self, *_args, **_kwargs):
        return self

    def order_by(self, *_args, **_kwargs):
        return self

    def all(self):
        return self._items


class FakeDB:
    def query(self, _model):
        model_name = getattr(_model, "__name__", "")
        if model_name == "AllocationRule":
            return FakeQuery([])
        rows = [
            FakeResource(
                "ocid1.instance.oc1..aaaaaaaaaaaaaaaa",
                name="vm-finance-01",
                rtype="compute.instance",
                compartment_id="finance",
            )
        ]
        return FakeQuery(rows)


class TaggedFakeDB:
    def query(self, _model):
        model_name = getattr(_model, "__name__", "")
        if model_name == "AllocationRule":
            return FakeQuery([])
        rows = [
            FakeResource(
                "ocid1.instance.oc1..aaaaaaaaaaaaaaaa",
                name="vm-finance-01",
                rtype="compute.instance",
                compartment_id="finance",
                details={"freeform_tags": {"environment": "Prod", "owner_team": "FinOps", "application": "Billing"}},
            ),
            FakeResource(
                "ocid1.instance.oc1..bbbbbbbbbbbbbbbb",
                name="vm-it-01",
                rtype="compute.instance",
                compartment_id="it",
                details={"freeform_tags": {"environment": "NonProd", "owner_team": "Platform", "application": "Portal"}},
            ),
        ]
        return FakeQuery(rows)


def test_breakdown_schema_stability(monkeypatch):
    monkeypatch.setattr(costs, "get_cost_calculator", lambda: FakeCalcBreakdown())
    response = client.get(
        "/api/v1/costs/breakdown?group_by=service&start_date=2026-01-01&end_date=2026-01-31&compare=previous&limit=8&min_share_pct=0.5"
    )
    assert response.status_code == 200
    payload = response.json()
    assert set(payload.keys()) == {"success", "data"}
    assert set(payload["data"].keys()) == {"group_by", "period", "totals", "items"}
    assert set(payload["data"]["period"].keys()) == {"start_date", "end_date", "days"}
    assert set(payload["data"]["totals"].keys()) == {"current", "previous"}
    assert set(payload["data"]["items"][0].keys()) == {"name", "current", "previous", "delta_abs", "delta_pct", "share_pct"}


def test_breakdown_end_date_inclusive_and_previous_period(monkeypatch):
    calc = FakeCalcBreakdown()
    monkeypatch.setattr(costs, "get_cost_calculator", lambda: calc)
    response = client.get(
        "/api/v1/costs/breakdown?group_by=service&start_date=2026-01-01&end_date=2026-01-31&compare=previous"
    )
    assert response.status_code == 200
    first_start, first_end = calc.service_calls[0]
    second_start, second_end = calc.service_calls[1]
    assert first_start == datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
    assert first_end == datetime(2026, 2, 1, 0, 0, tzinfo=UTC)
    assert second_start == datetime(2025, 12, 1, 0, 0, tzinfo=UTC)
    assert second_end == datetime(2026, 1, 1, 0, 0, tzinfo=UTC)


def test_breakdown_other_bucket_and_share_sum(monkeypatch):
    monkeypatch.setattr(costs, "get_cost_calculator", lambda: FakeCalcBreakdownMany())
    response = client.get(
        "/api/v1/costs/breakdown?group_by=service&start_date=2026-01-01&end_date=2026-01-31&limit=3&min_share_pct=0.5"
    )
    assert response.status_code == 200
    data = response.json()["data"]
    items = data["items"]
    names = [item["name"] for item in items]
    assert names[:3] == ["A", "B", "C"]
    assert names[-1] == "Other"
    other = items[-1]
    assert other["current"] == 280.0  # D..J
    assert other["previous"] == 280.0
    share_sum = sum(item["share_pct"] for item in items)
    assert abs(share_sum - 100.0) <= 0.2


def test_breakdown_empty_range_behavior(monkeypatch):
    monkeypatch.setattr(costs, "get_cost_calculator", lambda: FakeCalcEmpty())
    response = client.get(
        "/api/v1/costs/breakdown?group_by=service&start_date=2026-01-01&end_date=2026-01-31"
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["totals"]["current"] == 0.0
    assert data["totals"]["previous"] == 0.0
    assert data["items"] == []


def test_movers_previous_period_and_direction(monkeypatch):
    calc = FakeCalcMovers()
    monkeypatch.setattr(costs, "get_cost_calculator", lambda: calc)
    response_up = client.get(
        "/api/v1/costs/movers?group_by=service&start_date=2026-01-01&end_date=2026-01-31&direction=up"
    )
    assert response_up.status_code == 200
    up_items = response_up.json()["data"]["items"]
    assert up_items[0]["name"] == "Compute"
    assert up_items[0]["delta_abs"] == 100.0

    calc_down = FakeCalcMovers()
    monkeypatch.setattr(costs, "get_cost_calculator", lambda: calc_down)
    response_down = client.get(
        "/api/v1/costs/movers?group_by=service&start_date=2026-01-01&end_date=2026-01-31&direction=down"
    )
    assert response_down.status_code == 200
    down_items = response_down.json()["data"]["items"]
    assert down_items[0]["name"] == "Storage"
    assert down_items[0]["delta_abs"] == -20.0

    first_start, first_end = calc.service_calls[0]
    second_start, second_end = calc.service_calls[1]
    assert first_start == datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
    assert first_end == datetime(2026, 2, 1, 0, 0, tzinfo=UTC)
    assert second_start == datetime(2025, 12, 1, 0, 0, tzinfo=UTC)
    assert second_end == datetime(2026, 1, 1, 0, 0, tzinfo=UTC)


def test_movers_empty_range_behavior(monkeypatch):
    monkeypatch.setattr(costs, "get_cost_calculator", lambda: FakeCalcEmpty())
    response = client.get(
        "/api/v1/costs/movers?group_by=service&start_date=2026-01-01&end_date=2026-01-31"
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["items"] == []


def test_movers_resource_metadata_fallback(monkeypatch):
    monkeypatch.setattr(costs, "get_cost_calculator", lambda: FakeCalcMovers())
    app.dependency_overrides[costs.get_db] = lambda: FakeDB()
    try:
        response = client.get(
            "/api/v1/costs/movers?group_by=resource&start_date=2026-01-01&end_date=2026-01-31&direction=both"
        )
        assert response.status_code == 200
        items = response.json()["data"]["items"]
        assert any(i["name"] == "vm-finance-01" and i["type"] == "compute.instance" for i in items)
        # Second resource has no metadata in DB and should fall back to short OCID.
        assert any(i["name"] == "bbbbbbbbbbbbbbbb" for i in items)
    finally:
        app.dependency_overrides.pop(costs.get_db, None)


def test_breakdown_group_by_variants(monkeypatch):
    monkeypatch.setattr(costs, "get_cost_calculator", lambda: FakeCalcMovers())
    app.dependency_overrides[costs.get_db] = lambda: TaggedFakeDB()
    try:
        for group_by in ["compartment", "env", "team", "app"]:
            response = client.get(
                f"/api/v1/costs/breakdown?group_by={group_by}&start_date=2026-01-01&end_date=2026-01-31&compare=previous"
            )
            assert response.status_code == 200
            data = response.json()["data"]
            assert data["group_by"] == group_by
            assert isinstance(data["items"], list)
    finally:
        app.dependency_overrides.pop(costs.get_db, None)


def test_breakdown_mapping_health_for_allocation_dimensions(monkeypatch):
    monkeypatch.setattr(costs, "get_cost_calculator", lambda: FakeCalcMovers())
    app.dependency_overrides[costs.get_db] = lambda: TaggedFakeDB()
    try:
        response = client.get(
            "/api/v1/costs/breakdown?group_by=team&start_date=2026-01-01&end_date=2026-01-31&compare=previous"
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert "mapping_health" in data
        assert set(data["mapping_health"].keys()) == {"unowned_cost", "low_confidence_cost"}
    finally:
        app.dependency_overrides.pop(costs.get_db, None)


def test_movers_both_direction_sorting_stability(monkeypatch):
    monkeypatch.setattr(costs, "get_cost_calculator", lambda: FakeCalcMovers())
    response = client.get(
        "/api/v1/costs/movers?group_by=service&start_date=2026-01-01&end_date=2026-01-31&direction=both"
    )
    assert response.status_code == 200
    items = response.json()["data"]["items"]
    # Stable ordering by absolute delta then name.
    assert [i["name"] for i in items][:3] == ["Compute", "Storage", "Network"]

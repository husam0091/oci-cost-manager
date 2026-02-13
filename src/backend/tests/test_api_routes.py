from datetime import datetime
from types import SimpleNamespace

from fastapi.testclient import TestClient

from main import app
from api.routes import compartments, costs


client = TestClient(app)


def test_health_oci_endpoint_success(monkeypatch):
    class FakeOCIClient:
        region = "us-phoenix-1"

        def get_tenancy(self):
            return SimpleNamespace(name="Demo Tenancy")

    monkeypatch.setattr("api.routes.health.get_oci_client", lambda: FakeOCIClient())

    response = client.get("/api/v1/health/oci")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "healthy"
    assert payload["tenancy_name"] == "Demo Tenancy"
    assert payload["region"] == "us-phoenix-1"


def test_list_compartments_returns_expected_shape(monkeypatch):
    now = datetime(2026, 1, 1, 10, 0, 0)
    fake_compartment = SimpleNamespace(
        id="ocid1.compartment.oc1..aaaa",
        name="Finance",
        description="Finance workloads",
        compartment_id="ocid1.tenancy.oc1..root",
        lifecycle_state="ACTIVE",
        time_created=now,
    )

    class FakeOCIClient:
        def list_compartments(self, parent_id=None):
            assert parent_id is None
            return [fake_compartment]

    monkeypatch.setattr(compartments, "get_oci_client", lambda: FakeOCIClient())

    response = client.get("/api/v1/compartments")
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["meta"]["total"] == 1
    assert payload["data"][0]["id"] == fake_compartment.id
    assert payload["data"][0]["time_created"] == now.isoformat()


def test_compartment_tree_builds_hierarchy(monkeypatch):
    tenancy = SimpleNamespace(id="tenancy-root", name="RootTenancy")
    child = SimpleNamespace(
        id="child-1",
        name="Engineering",
        description="Eng",
        compartment_id="tenancy-root",
    )

    class FakeOCIClient:
        def get_tenancy(self):
            return tenancy

        def list_compartments(self):
            return [child]

    monkeypatch.setattr(compartments, "get_oci_client", lambda: FakeOCIClient())

    response = client.get("/api/v1/compartments/tree")
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["data"]["id"] == "tenancy-root"
    assert len(payload["data"]["children"]) == 1
    assert payload["data"]["children"][0]["id"] == "child-1"


def test_costs_endpoint_uses_cached_payload_when_available(monkeypatch):
    cached_payload = {
        "period": "monthly",
        "start_date": "2026-02-01T00:00:00",
        "end_date": "2026-02-07T00:00:00",
        "total": 123.45,
        "by_service": {"Compute": 123.45},
    }

    monkeypatch.setattr(costs, "get_cached", lambda key: cached_payload)
    monkeypatch.setattr(costs, "set_cached", lambda *args, **kwargs: None)

    response = client.get("/api/v1/costs")
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["cached"] is True
    assert payload["data"]["total"] == 123.45


def test_costs_endpoint_computes_and_caches_when_cache_miss(monkeypatch):
    class FakeCalculator:
        def get_costs_by_service(self, start, end):
            return {"Compute": 50.0, "Storage": 25.0}

    captured = {}

    monkeypatch.setattr(costs, "get_cached", lambda key: None)
    monkeypatch.setattr(costs, "get_cost_calculator", lambda: FakeCalculator())

    def fake_set_cached(key, value, ttl):
        captured["key"] = key
        captured["value"] = value
        captured["ttl"] = ttl

    monkeypatch.setattr(costs, "set_cached", fake_set_cached)

    response = client.get("/api/v1/costs?period=monthly&refresh=true")
    assert response.status_code == 200
    payload = response.json()

    assert payload["success"] is True
    assert payload["cached"] is False
    assert payload["data"]["total"] == 75.0
    assert payload["data"]["by_service"]["Compute"] == 50.0
    assert captured["ttl"] == costs.COST_CACHE_TTL

from types import SimpleNamespace

from fastapi.testclient import TestClient

from main import app
from api.routes import governance
from core.models import AllocationRule
from services.allocation import evaluate_allocation


client = TestClient(app)


class _FakeCalc:
    def __init__(self):
        self.calls = 0

    def get_costs_by_resource(self, start, end, include_skus=True):
        self.calls += 1
        if self.calls == 1:
            return [
                {"resource_id": "r1", "compartment_name": "finance", "total_cost": 100.0, "skus": [{"sku_name": "Compute VM"}]},
                {"resource_id": "r2", "compartment_name": "it", "total_cost": 50.0, "skus": [{"sku_name": "Block Storage"}]},
            ]
        return [
            {"resource_id": "r1", "compartment_name": "finance", "total_cost": 80.0, "skus": [{"sku_name": "Compute VM"}]},
            {"resource_id": "r2", "compartment_name": "it", "total_cost": 40.0, "skus": [{"sku_name": "Block Storage"}]},
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


class _Resource:
    def __init__(self, ocid, details=None, name=None, compartment_id=None):
        self.ocid = ocid
        self.details = details or {}
        self.name = name or ocid
        self.compartment_id = compartment_id or "unknown"


class _DBForCoverage:
    def query(self, model):
        name = getattr(model, "__name__", "")
        if name == "Resource":
            return _Q([
                _Resource("r1", details={"freeform_tags": {"environment": "prod", "owner_team": "finops", "application": "billing"}}),
                _Resource("r2", details={}),
            ])
        if name == "AllocationRule":
            return _Q([])
        return _Q([])


def _override_admin():
    return {"sub": "tester"}


def test_rule_evaluation_deterministic_by_priority_and_id():
    resource = SimpleNamespace(
        name="vm-finance-01",
        compartment_id="finance",
        details={"freeform_tags": {}},
    )
    rules = [
        AllocationRule(id=2, name="low-pri", is_enabled=True, match_type="resource_name", match_expression="vm-", set_env="nonprod", set_team="platform", set_app="portal", priority=200),
        AllocationRule(id=1, name="high-pri", is_enabled=True, match_type="resource_name", match_expression="vm-finance", set_env="prod", set_team="finops", set_app="billing", priority=10),
    ]
    result = evaluate_allocation(resource, rules, compartment_name="finance", sku_text="")
    assert result.env == "prod"
    assert result.team == "finops"
    assert result.app == "billing"
    assert result.allocation_confidence == "medium"


def test_governance_tag_coverage_schema_and_math(monkeypatch):
    monkeypatch.setattr(governance, "get_cost_calculator", lambda: _FakeCalc())
    app.dependency_overrides[governance.get_db] = lambda: _DBForCoverage()
    try:
        response = client.get("/api/v1/governance/tag-coverage?start_date=2026-01-01&end_date=2026-01-31")
        assert response.status_code == 200
        payload = response.json()
        assert set(payload.keys()) == {"success", "data"}
        assert set(payload["data"].keys()) == {
            "period",
            "totals",
            "coverage",
            "unowned_cost",
            "top_missing_compartments",
            "top_missing_services",
        }
        assert payload["data"]["totals"]["current"] == 150.0
        assert payload["data"]["unowned_cost"]["current"] == 50.0
        assert payload["data"]["coverage"]["env_pct"] == 50.0
    finally:
        app.dependency_overrides.pop(governance.get_db, None)


def test_allocation_rules_crud_contract():
    app.dependency_overrides[governance._require_admin] = _override_admin
    try:
        create = client.post(
            "/api/v1/admin/allocation-rules",
            json={
                "name": "Finance fallback",
                "is_enabled": True,
                "match_type": "compartment",
                "match_expression": "finance",
                "set_env": "prod",
                "set_team": "finops",
                "set_app": "billing",
                "priority": 10,
            },
        )
        assert create.status_code == 200
        rule_id = create.json()["data"]["id"]

        listing = client.get("/api/v1/admin/allocation-rules")
        assert listing.status_code == 200
        assert set(listing.json().keys()) == {"success", "data"}
        assert any(r["id"] == rule_id for r in listing.json()["data"])

        update = client.put(
            f"/api/v1/admin/allocation-rules/{rule_id}",
            json={
                "name": "Finance fallback v2",
                "is_enabled": True,
                "match_type": "compartment",
                "match_expression": "finance",
                "set_env": "prod",
                "set_team": "finops",
                "set_app": "billing-v2",
                "priority": 5,
            },
        )
        assert update.status_code == 200
        assert update.json()["success"] is True

        delete = client.delete(f"/api/v1/admin/allocation-rules/{rule_id}")
        assert delete.status_code == 200
        assert delete.json()["success"] is True
    finally:
        app.dependency_overrides.pop(governance._require_admin, None)


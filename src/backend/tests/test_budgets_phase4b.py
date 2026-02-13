from dataclasses import dataclass

from fastapi.testclient import TestClient

from api.routes import budgets as budget_routes
from main import app


client = TestClient(app)


@dataclass
class _Status:
    budget_id: str
    budget_name: str
    scope_type: str
    scope_value: str
    current_spend: float
    budget_limit: float
    utilization_pct: float
    forecast_end_of_month: float
    breach_level: str
    days_remaining: int
    explanation: str
    latest_threshold_crossed: int | None


def test_budget_crud_and_schema_stability():
    create = client.post(
        "/api/v1/budgets",
        json={
            "name": "Global Budget",
            "scope_type": "global",
            "scope_value": "global",
            "period": "monthly",
            "limit_amount": 1000,
            "currency": "USD",
            "alert_thresholds": [50, 75, 90, 100],
            "compare_mode": "actual",
            "enabled": True,
            "owner": "finops@example.com",
        },
    )
    assert create.status_code == 200
    payload = create.json()
    assert set(payload.keys()) == {"success", "data"}
    assert "budget_id" in payload["data"]
    bid = payload["data"]["budget_id"]

    listed = client.get("/api/v1/budgets")
    assert listed.status_code == 200
    rows = listed.json()["data"]
    row = next(r for r in rows if r["budget_id"] == bid)
    assert set(row.keys()) == {
        "budget_id",
        "name",
        "scope_type",
        "scope_value",
        "include_children",
        "period",
        "limit_amount",
        "currency",
        "growth_cap_pct",
        "forecast_guardrail_pct",
        "alert_thresholds",
        "compare_mode",
        "enabled",
        "notifications_enabled",
        "owner",
        "created_at",
        "updated_at",
    }

    update = client.put(
        f"/api/v1/budgets/{bid}",
        json={
            "name": "Global Budget Updated",
            "scope_type": "global",
            "scope_value": "global",
            "period": "monthly",
            "limit_amount": 1500,
            "currency": "USD",
            "alert_thresholds": [60, 80, 100],
            "compare_mode": "forecast",
            "enabled": True,
            "owner": "finance@example.com",
        },
    )
    assert update.status_code == 200
    assert update.json()["data"]["name"] == "Global Budget Updated"

    delete = client.delete(f"/api/v1/budgets/{bid}")
    assert delete.status_code == 200
    assert delete.json() == {"success": True}


def test_budget_status_schema(monkeypatch):
    monkeypatch.setattr(
        budget_routes,
        "evaluate_budget_statuses",
        lambda db, persist_alerts=True: [
            _Status(
                budget_id="bud_1",
                budget_name="Global",
                scope_type="global",
                scope_value="global",
                current_spend=720.0,
                budget_limit=1000.0,
                utilization_pct=72.0,
                forecast_end_of_month=980.0,
                breach_level="warning",
                days_remaining=8,
                explanation="Budget utilization is approaching limit.",
                latest_threshold_crossed=75,
            )
        ],
    )
    response = client.get("/api/v1/budgets/status")
    assert response.status_code == 200
    payload = response.json()
    assert set(payload.keys()) == {"success", "data"}
    assert len(payload["data"]) == 1
    item = payload["data"][0]
    assert set(item.keys()) == {
        "budget_id",
        "budget_name",
        "scope_type",
        "scope_value",
        "current_spend",
        "budget_limit",
        "utilization_pct",
        "forecast_end_of_month",
        "breach_level",
        "days_remaining",
        "explanation",
        "narrative",
        "latest_threshold_crossed",
    }

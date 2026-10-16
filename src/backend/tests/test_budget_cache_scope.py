from types import SimpleNamespace
from fastapi.testclient import TestClient
from api.routes import budgets
from core.rbac import Principal
from main import app


def test_budget_cache_is_partitioned_by_identity_and_updated_scope(monkeypatch):
    principal = Principal("admin", "admin", [], [], [], [])
    monkeypatch.setattr(budgets, "resolve_principal", lambda *a, **kw: principal)
    calls = []

    def evaluate(*args, **kwargs):
        calls.append(True)
        return [
            SimpleNamespace(
                budget_id=t,
                budget_name=t,
                scope_type="team",
                scope_value=t,
                current_spend=50,
                budget_limit=100,
                utilization_pct=50,
                forecast_end_of_month=80,
                breach_level="none",
                days_remaining=5,
                explanation="test",
                latest_threshold_crossed=None,
            )
            for t in ["A", "B"]
        ]

    monkeypatch.setattr(budgets, "evaluate_budget_statuses", evaluate)
    client = TestClient(app)
    assert len(client.get("/api/v1/budgets/status").json()["data"]) == 2
    principal = Principal("analyst", "finops", ["A"], [], [], [])
    assert [
        r["budget_id"] for r in client.get("/api/v1/budgets/status").json()["data"]
    ] == ["A"]
    client.get("/api/v1/budgets/status")
    assert len(calls) == 2
    principal.allowed_teams = ["B"]
    assert [
        r["budget_id"] for r in client.get("/api/v1/budgets/status").json()["data"]
    ] == ["B"]
    assert len(calls) == 3

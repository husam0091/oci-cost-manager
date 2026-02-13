from fastapi.testclient import TestClient

from api.routes import recommendations
from main import app
from services import recommendations as rec_service


client = TestClient(app)


class FakeCalcRecommendations:
    def get_costs_by_resource(self, start, end, include_skus=True, compartment_id=None):
        if start.month == 1:
            return [
                {
                    "resource_id": "r-unattached",
                    "compartment_id": "comp-a",
                    "compartment_name": "Comp A",
                    "total_cost": 120.0,
                    "skus": [{"sku_name": "Block Volume - Storage", "cost": 120.0}],
                },
                {
                    "resource_id": "r-compute",
                    "compartment_id": "comp-a",
                    "compartment_name": "Comp A",
                    "total_cost": 40.0,
                    "skus": [{"sku_name": "Compute VM", "cost": 40.0}],
                },
                {
                    "resource_id": "r-windows",
                    "compartment_id": "comp-b",
                    "compartment_name": "Comp B",
                    "total_cost": 90.0,
                    "skus": [{"sku_name": "Windows OS", "cost": 90.0}],
                },
                {
                    "resource_id": "r-sql",
                    "compartment_id": "comp-b",
                    "compartment_name": "Comp B",
                    "total_cost": 80.0,
                    "skus": [{"sku_name": "Microsoft SQL Server Enterprise", "cost": 80.0}],
                },
                {
                    "resource_id": "r-backup",
                    "compartment_id": "comp-c",
                    "compartment_name": "Comp C",
                    "total_cost": 60.0,
                    "skus": [{"sku_name": "Volume Backup", "cost": 60.0}],
                },
            ]
        return [
            {"resource_id": "r-unattached", "total_cost": 100.0, "skus": [{"sku_name": "Block Volume - Storage", "cost": 100.0}]},
            {"resource_id": "r-compute", "total_cost": 60.0, "skus": [{"sku_name": "Compute VM", "cost": 60.0}]},
            {"resource_id": "r-windows", "total_cost": 85.0, "skus": [{"sku_name": "Windows OS", "cost": 85.0}]},
            {"resource_id": "r-sql", "total_cost": 70.0, "skus": [{"sku_name": "Microsoft SQL Server Enterprise", "cost": 70.0}]},
            {"resource_id": "r-backup", "total_cost": 55.0, "skus": [{"sku_name": "Volume Backup", "cost": 55.0}]},
        ]


class _Resource:
    def __init__(self, ocid, name, rtype, compartment_id, status="RUNNING", shape=None, details=None):
        self.ocid = ocid
        self.name = name
        self.type = rtype
        self.compartment_id = compartment_id
        self.status = status
        self.shape = shape
        self.details = details or {}


class _Compartment:
    def __init__(self, cid, name):
        self.id = cid
        self.name = name


class _Q:
    def __init__(self, rows):
        self.rows = rows

    def filter(self, *_args, **_kwargs):
        return self

    def order_by(self, *_args, **_kwargs):
        return self

    def all(self):
        return self.rows


class _FakeDB:
    def query(self, model):
        name = getattr(model, "__name__", "")
        if name == "Resource":
            return _Q(
                [
                    _Resource("r-unattached", "unattached-vol", "block_volume", "comp-a", details={"attachment_state": "UNATTACHED", "size_in_gbs": 1200}),
                    _Resource("r-compute", "vm-idle", "compute.instance", "comp-a", status="STOPPED", shape="VM.Standard.E5.Flex", details={"ocpus": 4}),
                    _Resource("r-windows", "vm-windows", "windows_server", "comp-b", details={"image_name": "Windows-2022"}),
                    _Resource("r-sql", "vm-sql", "sql_server", "comp-b", details={"image_name": "SQL Server 2022"}),
                    _Resource("r-backup", "backup-old", "volume_backup", "comp-c", details={"time_created": "2025-11-01T00:00:00Z"}),
                ]
            )
        if name == "Compartment":
            return _Q([_Compartment("comp-a", "Comp A"), _Compartment("comp-b", "Comp B"), _Compartment("comp-c", "Comp C")])
        if name == "AllocationRule":
            return _Q([])
        return _Q([])


def test_recommendations_summary_schema_and_math(monkeypatch):
    monkeypatch.setattr(rec_service, "get_cost_calculator", lambda: FakeCalcRecommendations())
    app.dependency_overrides[recommendations.get_db] = lambda: _FakeDB()
    try:
        resp = client.get("/api/v1/recommendations/summary?start_date=2026-01-01&end_date=2026-01-31")
        assert resp.status_code == 200
        payload = resp.json()
        assert set(payload.keys()) == {"success", "data"}
        assert set(payload["data"].keys()) == {"period", "totals", "by_category"}
        assert set(payload["data"]["totals"].keys()) == {"potential_savings_monthly", "recommendation_count", "high_confidence_savings"}
        assert payload["data"]["totals"]["potential_savings_monthly"] >= payload["data"]["totals"]["high_confidence_savings"]
        assert payload["data"]["totals"]["recommendation_count"] > 0
    finally:
        app.dependency_overrides.pop(recommendations.get_db, None)


def test_recommendations_list_schema_and_determinism(monkeypatch):
    monkeypatch.setattr(rec_service, "get_cost_calculator", lambda: FakeCalcRecommendations())
    app.dependency_overrides[recommendations.get_db] = lambda: _FakeDB()
    try:
        url = "/api/v1/recommendations/list?start_date=2026-01-01&end_date=2026-01-31"
        one = client.get(url)
        two = client.get(url)
        assert one.status_code == 200
        assert two.status_code == 200
        items_a = one.json()["data"]["items"]
        items_b = two.json()["data"]["items"]
        assert len(items_a) == len(items_b)
        assert [x["recommendation_id"] for x in items_a] == [x["recommendation_id"] for x in items_b]
        assert set(items_a[0].keys()) == {
            "recommendation_id",
            "category",
            "type",
            "resource_ref",
            "resource_name",
            "compartment_id",
            "compartment_name",
            "team",
            "app",
            "env",
            "current_cost",
            "estimated_savings",
            "confidence",
            "reason",
            "recommendation",
        }
    finally:
        app.dependency_overrides.pop(recommendations.get_db, None)


def test_recommendation_resource_details(monkeypatch):
    monkeypatch.setattr(rec_service, "get_cost_calculator", lambda: FakeCalcRecommendations())
    app.dependency_overrides[recommendations.get_db] = lambda: _FakeDB()
    try:
        list_resp = client.get("/api/v1/recommendations/list?start_date=2026-01-01&end_date=2026-01-31")
        rec_id = list_resp.json()["data"]["items"][0]["recommendation_id"]
        detail = client.get(f"/api/v1/recommendations/resource/{rec_id}?start_date=2026-01-01&end_date=2026-01-31")
        assert detail.status_code == 200
        data = detail.json()["data"]
        assert set(data.keys()) == {
            "recommendation_id",
            "type",
            "category",
            "resource_ref",
            "resource_name",
            "confidence",
            "reason",
            "recommendation",
            "why_flagged",
            "next_steps",
            "cost_history_snapshot",
        }
        assert data["cost_history_snapshot"]["current"] >= 0
    finally:
        app.dependency_overrides.pop(recommendations.get_db, None)


def test_recommendations_empty_range(monkeypatch):
    class EmptyCalc:
        def get_costs_by_resource(self, start, end, include_skus=True, compartment_id=None):
            return []

    monkeypatch.setattr(rec_service, "get_cost_calculator", lambda: EmptyCalc())
    app.dependency_overrides[recommendations.get_db] = lambda: _FakeDB()
    try:
        resp = client.get("/api/v1/recommendations/list?start_date=2026-01-01&end_date=2026-01-31")
        assert resp.status_code == 200
        assert resp.json()["data"]["items"] == []
    finally:
        app.dependency_overrides.pop(recommendations.get_db, None)

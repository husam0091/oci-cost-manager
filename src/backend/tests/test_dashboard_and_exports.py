from pathlib import Path
from types import SimpleNamespace
import json

from fastapi.testclient import TestClient

from main import app
from api.routes import admin, dashboard


client = TestClient(app)


class FakeCalculator:
    def get_costs_by_service(self, start, end):
        return {"Compute": 100.0, "Storage": 50.0}

    def get_costs_by_resource(self, start, end, include_skus=True, compartment_id=None):
        return [
            {
                "resource_id": "ocid1.instance.oc1..demo",
                "compartment_id": "comp-1",
                "compartment_name": "Compartment A",
                "total_cost": 75.0,
                "skus": [{"sku_name": "Windows OS", "cost": 25.0}, {"sku_name": "Standard - E5", "cost": 50.0}],
            },
            {
                "resource_id": "ocid1.volume.oc1..demo",
                "compartment_id": "comp-1",
                "compartment_name": "Compartment A",
                "total_cost": 30.0,
                "skus": [{"sku_name": "Block Volume - Storage", "cost": 30.0}],
            },
        ]


def test_dashboard_summary_end_date_is_inclusive(monkeypatch):
    monkeypatch.setattr(dashboard, "get_cost_calculator", lambda: FakeCalculator())
    response = client.get("/api/v1/dashboard/summary?start_date=2026-01-01&end_date=2026-01-31")
    assert response.status_code == 200
    payload = response.json()["data"]
    # Inclusive date range should contain 31 days for Jan 1-31.
    assert payload["period"]["start_date"] == "2026-01-01"
    assert payload["period"]["end_date"] == "2026-01-31"
    assert payload["period"]["days"] == 31


def test_export_generate_creates_manifest_and_validation(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(admin, "get_cost_calculator", lambda: FakeCalculator())
    monkeypatch.setattr(admin, "get_app_settings", lambda: SimpleNamespace(export_dir=str(tmp_path), app_version="1.0.0", app_name="OCI Cost Manager"))
    app.dependency_overrides[admin._require_admin] = lambda: {"sub": "tester"}

    try:
        response = client.post(
            "/api/v1/admin/exports/generate",
            json={
                "report_type": "executive_summary_monthly",
                "start_date": "2026-01-01",
                "end_date": "2026-01-31",
                "options": {"top_n": 5, "compare": "previous"},
            },
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert set(data.keys()) == {"files"}
        assert set(data["files"].keys()) == {"xlsx", "manifest", "validation"}
        assert data["files"]["xlsx"]["name"].endswith(".xlsx")
        assert data["files"]["manifest"]["name"].endswith(".manifest.json")
        assert data["files"]["validation"]["name"].endswith(".validation.json")

        assert (tmp_path / data["files"]["xlsx"]["name"]).exists()
        manifest_path = tmp_path / data["files"]["manifest"]["name"]
        validation_path = tmp_path / data["files"]["validation"]["name"]
        assert manifest_path.exists()
        assert validation_path.exists()

        manifest = manifest_path.read_text(encoding="utf-8")
        assert "report_type" in manifest
        assert "selected_filters" in manifest
        assert "generated_at" in manifest
        assert "generated_by" in manifest
        assert "actor" in manifest
        assert "oci_auth_mode" in manifest
        assert "oci_config_profile" in manifest
        assert "scan_run_id" in manifest
        assert "start_date" in manifest and "end_date" in manifest

        validation = validation_path.read_text(encoding="utf-8")
        assert "row_count" in validation
        assert "totals_checksum" in validation
        assert "low_confidence_count" in validation
        assert "warnings" in validation

        list_response = client.get("/api/v1/admin/exports/list")
        assert list_response.status_code == 200
        assert isinstance(list_response.json()["data"], list)
    finally:
        app.dependency_overrides.pop(admin._require_admin, None)


def test_export_snapshot_includes_required_metadata(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(admin, "get_app_settings", lambda: SimpleNamespace(export_dir=str(tmp_path), app_version="1.0.0", app_name="OCI Cost Manager"))
    app.dependency_overrides[admin._require_admin] = lambda: {"sub": "tester"}
    try:
        response = client.post(
            "/api/v1/admin/exports/snapshot",
            json={
                "name": "metadata-check",
                "report_type": "snapshot",
                "export_format": "json",
                "include_scan_runs": False,
            },
        )
        assert response.status_code == 200
        file_name = response.json()["data"]["file_name"]
        payload = json.loads((tmp_path / file_name).read_text(encoding="utf-8"))
        meta = payload["meta"]
        assert "generated_at" in meta
        assert meta.get("generated_by") == "tester"
        assert meta.get("actor") == "tester"
        assert "oci_auth_mode" in meta
        assert "oci_config_profile" in meta
        assert "scan_run_id" in meta
    finally:
        app.dependency_overrides.pop(admin._require_admin, None)


def test_inventory_summary_report_generates_non_negative_totals(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(admin, "get_cost_calculator", lambda: FakeCalculator())
    monkeypatch.setattr(admin, "get_app_settings", lambda: SimpleNamespace(export_dir=str(tmp_path), app_version="1.0.0", app_name="OCI Cost Manager"))
    app.dependency_overrides[admin._require_admin] = lambda: {"sub": "tester"}
    try:
        response = client.post(
            "/api/v1/admin/exports/generate",
            json={
                "report_type": "inventory_summary_by_compartment",
                "start_date": "2026-01-01",
                "end_date": "2026-01-31",
                "options": {"compare": "previous"},
            },
        )
        assert response.status_code == 200
        validation_name = response.json()["data"]["files"]["validation"]["name"]
        validation = (tmp_path / validation_name).read_text(encoding="utf-8")
        assert "current_total_cost" in validation
        assert "previous_total_cost" in validation
        assert "unmapped_unallocated_pct" in validation
    finally:
        app.dependency_overrides.pop(admin._require_admin, None)


def test_export_generate_empty_range_contains_warning(monkeypatch, tmp_path: Path):
    class EmptyCalculator:
        def get_costs_by_service(self, start, end):
            return {}

        def get_costs_by_resource(self, start, end, include_skus=True):
            return []

    monkeypatch.setattr(admin, "get_cost_calculator", lambda: EmptyCalculator())
    monkeypatch.setattr(admin, "get_app_settings", lambda: SimpleNamespace(export_dir=str(tmp_path), app_version="1.0.0", app_name="OCI Cost Manager"))
    app.dependency_overrides[admin._require_admin] = lambda: {"sub": "tester"}
    try:
        response = client.post(
            "/api/v1/admin/exports/generate",
            json={
                "report_type": "cost_by_service",
                "start_date": "2026-01-01",
                "end_date": "2026-01-31",
                "options": {"compare": "previous"},
            },
        )
        assert response.status_code == 200
        validation_name = response.json()["data"]["files"]["validation"]["name"]
        validation = (tmp_path / validation_name).read_text(encoding="utf-8")
        assert "No cost data for selected range" in validation
    finally:
        app.dependency_overrides.pop(admin._require_admin, None)


def test_export_generate_optimization_recommendations(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(admin, "get_cost_calculator", lambda: FakeCalculator())
    monkeypatch.setattr(admin, "get_app_settings", lambda: SimpleNamespace(export_dir=str(tmp_path), app_version="1.0.0", app_name="OCI Cost Manager"))
    app.dependency_overrides[admin._require_admin] = lambda: {"sub": "tester"}
    try:
        response = client.post(
            "/api/v1/admin/exports/generate",
            json={
                "report_type": "optimization_recommendations",
                "start_date": "2026-01-01",
                "end_date": "2026-01-31",
                "options": {"compare": "previous"},
            },
        )
        assert response.status_code == 200
        manifest_name = response.json()["data"]["files"]["manifest"]["name"]
        validation_name = response.json()["data"]["files"]["validation"]["name"]
        manifest = (tmp_path / manifest_name).read_text(encoding="utf-8")
        validation = (tmp_path / validation_name).read_text(encoding="utf-8")
        assert "detection_rules_used" in manifest
        assert "confidence_criteria" in manifest
        assert "savings_non_negative" in validation
    finally:
        app.dependency_overrides.pop(admin._require_admin, None)


def test_export_generate_budget_health(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(admin, "get_cost_calculator", lambda: FakeCalculator())
    monkeypatch.setattr(admin, "get_app_settings", lambda: SimpleNamespace(export_dir=str(tmp_path), app_version="1.0.0", app_name="OCI Cost Manager"))
    app.dependency_overrides[admin._require_admin] = lambda: {"sub": "tester"}
    try:
        response = client.post(
            "/api/v1/admin/exports/generate",
            json={
                "report_type": "budget_health",
                "start_date": "2026-01-01",
                "end_date": "2026-01-31",
                "options": {"compare": "previous"},
            },
        )
        assert response.status_code == 200
        manifest_name = response.json()["data"]["files"]["manifest"]["name"]
        validation_name = response.json()["data"]["files"]["validation"]["name"]
        manifest = (tmp_path / manifest_name).read_text(encoding="utf-8")
        validation = (tmp_path / validation_name).read_text(encoding="utf-8")
        assert "evaluation_date" in manifest
        assert "forecast_method" in manifest
        assert "notification_channels_enabled" in manifest
        assert "narrative_rules_version" in manifest
        assert "savings_non_negative" in validation
    finally:
        app.dependency_overrides.pop(admin._require_admin, None)

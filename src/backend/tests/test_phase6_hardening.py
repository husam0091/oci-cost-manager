from dataclasses import dataclass

from fastapi import HTTPException
from fastapi.testclient import TestClient

from api.routes import actions as actions_route
from api.routes import admin as admin_route
from api.routes import budgets as budgets_route
from api.routes import recommendations as rec_route
from core.database import SessionLocal
from core.models import ActionRequest, Budget, Setting
from main import app

client = TestClient(app)


@dataclass
class _Principal:
    username: str = "admin"
    role: str = "admin"
    allowed_teams: list[str] = None
    allowed_apps: list[str] = None
    allowed_envs: list[str] = None
    allowed_compartment_ids: list[str] = None

    def __post_init__(self):
        self.allowed_teams = self.allowed_teams or []
        self.allowed_apps = self.allowed_apps or []
        self.allowed_envs = self.allowed_envs or []
        self.allowed_compartment_ids = self.allowed_compartment_ids or []

    @property
    def is_admin(self):
        return self.role == "admin"


def test_feature_flags_get_update():
    app.dependency_overrides[admin_route._require_admin] = lambda: {"sub": "admin"}
    try:
        update = client.post(
            "/api/v1/admin/settings/feature-flags",
            json={"enable_oci_executors": True, "enable_destructive_actions": False, "enable_budget_auto_eval": True, "enable_demo_mode": False},
        )
        assert update.status_code == 200
        data = update.json()["data"]
        assert set(data.keys()) == {"enable_oci_executors", "enable_destructive_actions", "enable_notifications", "enable_budget_auto_eval", "enable_demo_mode"}
        fetched = client.get("/api/v1/admin/settings/feature-flags")
        assert fetched.status_code == 200
    finally:
        app.dependency_overrides.pop(admin_route._require_admin, None)


def test_actions_viewer_cannot_create():
    app.dependency_overrides[actions_route._principal] = lambda: _Principal(role="viewer")
    try:
        response = client.post(
            "/api/v1/actions",
            json={
                "source": "manual",
                "category": "notify_only",
                "target_type": "policy",
                "target_ref": {},
                "proposed_change": {"executor_type": "notify_only"},
            },
        )
        assert response.status_code == 403
    finally:
        app.dependency_overrides.pop(actions_route._principal, None)


def test_actions_finops_cannot_run_moderate():
    app.dependency_overrides[actions_route._principal] = lambda: _Principal(role="finops")
    try:
        created = client.post(
            "/api/v1/actions",
            json={
                "source": "manual",
                "category": "cleanup",
                "target_type": "volume",
                "target_ref": {},
                "risk_level": "moderate",
                "proposed_change": {"executor_type": "cleanup_unattached_volume"},
            },
        )
        assert created.status_code == 200
        action_id = created.json()["data"]["action_id"]
        run = client.post(f"/api/v1/actions/{action_id}/run", json={"dry_run": True})
        assert run.status_code == 403
    finally:
        app.dependency_overrides.pop(actions_route._principal, None)


def test_actions_finops_can_run_safe():
    app.dependency_overrides[actions_route._principal] = lambda: _Principal(role="finops")
    try:
        created = client.post(
            "/api/v1/actions",
            json={
                "source": "manual",
                "category": "notify_only",
                "target_type": "policy",
                "target_ref": {},
                "risk_level": "safe",
                "proposed_change": {"executor_type": "notify_only"},
            },
        )
        assert created.status_code == 200
        action_id = created.json()["data"]["action_id"]
        run = client.post(f"/api/v1/actions/{action_id}/run", json={"dry_run": True})
        assert run.status_code == 200
    finally:
        app.dependency_overrides.pop(actions_route._principal, None)


def test_oci_executor_flag_gating_blocks_run():
    app.dependency_overrides[actions_route._principal] = lambda: _Principal(role="admin")
    try:
        db = SessionLocal()
        s = db.query(Setting).filter(Setting.id == 1).one_or_none()
        if s is None:
            s = Setting(id=1, username="admin", password_hash="x")
            db.add(s)
        s.enable_oci_executors = False
        db.commit()
        db.close()

        created = client.post(
            "/api/v1/actions",
            json={
                "source": "manual",
                "category": "tag_fix",
                "target_type": "tag",
                "target_ref": {"resource_id": "ocid1.instance"},
                "risk_level": "safe",
                "proposed_change": {"executor_type": "tag_fix_oci", "tags": {"env": "prod"}},
            },
        )
        action_id = created.json()["data"]["action_id"]
        run = client.post(f"/api/v1/actions/{action_id}/run", json={"dry_run": True})
        assert run.status_code == 403
    finally:
        app.dependency_overrides.pop(actions_route._principal, None)


def test_destructive_flag_blocks_live_cleanup():
    app.dependency_overrides[actions_route._principal] = lambda: _Principal(role="admin")
    try:
        db = SessionLocal()
        s = db.query(Setting).filter(Setting.id == 1).one_or_none()
        if s is None:
            s = Setting(id=1, username="admin", password_hash="x")
            db.add(s)
        s.enable_destructive_actions = False
        db.commit()
        db.close()

        created = client.post(
            "/api/v1/actions",
            json={
                "source": "manual",
                "category": "cleanup",
                "target_type": "volume",
                "target_ref": {"resource_id": "vol-x"},
                "risk_level": "safe",
                "proposed_change": {"executor_type": "cleanup_unattached_volume"},
            },
        )
        action_id = created.json()["data"]["action_id"]
        run = client.post(f"/api/v1/actions/{action_id}/run", json={"dry_run": False, "confirm_delete": True})
        assert run.status_code == 403
    finally:
        app.dependency_overrides.pop(actions_route._principal, None)


def test_recommendations_scope_filtering(monkeypatch):
    class _Rec:
        def __init__(self, rid, team):
            self.recommendation_id = rid
            self.category = "compute"
            self.type = "idle_compute"
            self.resource_ref = rid
            self.resource_name = rid
            self.compartment_id = "c1"
            self.compartment_name = "c1"
            self.team = team
            self.app = "a1"
            self.env = "prod"
            self.current_cost = 1.0
            self.estimated_savings = 0.5
            self.confidence = "high"
            self.reason = "r"
            self.recommendation = "x"
            self.why_flagged = ["x"]
            self.next_steps = ["x"]
            self.history = {"current": 1, "previous": 1, "delta_abs": 0}

    monkeypatch.setattr(rec_route, "generate_recommendations", lambda db, start, end_exclusive: {"items": [_Rec("r1", "alpha"), _Rec("r2", "beta")]})
    monkeypatch.setattr(rec_route, "resolve_principal", lambda db, token, strict=False: _Principal(role="engineer", allowed_teams=["alpha"]))
    response = client.get("/api/v1/recommendations/list?start_date=2026-01-01&end_date=2026-01-31")
    assert response.status_code == 200
    items = response.json()["data"]["items"]
    assert len(items) == 1
    assert items[0]["team"] == "alpha"


def test_budgets_scope_filtering(monkeypatch):
    monkeypatch.setattr(budgets_route, "resolve_principal", lambda db, token, strict=False: _Principal(role="finops", allowed_teams=["alpha"]))
    db = SessionLocal()
    try:
        if not db.query(Budget).filter(Budget.budget_id == "bud_scope_a").one_or_none():
            db.add(Budget(budget_id="bud_scope_a", name="A", scope_type="team", scope_value="alpha", limit_amount=100, alert_thresholds=[50], owner="o"))
        if not db.query(Budget).filter(Budget.budget_id == "bud_scope_b").one_or_none():
            db.add(Budget(budget_id="bud_scope_b", name="B", scope_type="team", scope_value="beta", limit_amount=100, alert_thresholds=[50], owner="o"))
        db.commit()
    finally:
        db.close()
    response = client.get("/api/v1/budgets")
    assert response.status_code == 200
    ids = {x["budget_id"] for x in response.json()["data"]}
    assert "bud_scope_a" in ids
    assert "bud_scope_b" not in ids


def test_ops_metrics_contract():
    response = client.get("/api/v1/ops/metrics")
    assert response.status_code == 200
    data = response.json()["data"]
    assert set(data.keys()) == {"app_version", "scans", "actions", "alerts", "budget_breaches", "cache_hit_ratio", "cache", "feature_flags"}


def test_health_live_and_ready_contracts():
    live = client.get("/api/v1/health/live")
    assert live.status_code == 200
    assert live.json().get("status") == "alive"
    ready = client.get("/api/v1/health/ready")
    assert ready.status_code == 200
    assert ready.json().get("status") == "ready"


def test_demo_mode_blocks_action_mutations():
    app.dependency_overrides[actions_route._principal] = lambda: _Principal(role="admin")
    try:
        db = SessionLocal()
        s = db.query(Setting).filter(Setting.id == 1).one_or_none()
        if s is None:
            s = Setting(id=1, username="admin", password_hash="x")
            db.add(s)
        s.enable_demo_mode = True
        db.commit()
        db.close()

        created = client.post(
            "/api/v1/actions",
            json={
                "source": "manual",
                "category": "notify_only",
                "target_type": "policy",
                "target_ref": {},
                "proposed_change": {"executor_type": "notify_only"},
            },
        )
        assert created.status_code == 403
    finally:
        db = SessionLocal()
        s = db.query(Setting).filter(Setting.id == 1).one_or_none()
        if s:
            s.enable_demo_mode = False
            db.commit()
        db.close()
        app.dependency_overrides.pop(actions_route._principal, None)


def test_ops_audit_export_generation(monkeypatch, tmp_path):
    monkeypatch.setattr(admin_route, "get_app_settings", lambda: type("C", (), {"export_dir": str(tmp_path), "app_version": "1.0.0", "app_name": "OCI Cost Manager"})())
    app.dependency_overrides[admin_route._require_admin] = lambda: {"sub": "admin"}
    try:
        response = client.post(
            "/api/v1/admin/exports/generate",
            json={
                "report_type": "ops_audit",
                "start_date": "2026-01-01",
                "end_date": "2026-01-31",
                "options": {"compare": "previous"},
            },
        )
        assert response.status_code == 200
    finally:
        app.dependency_overrides.pop(admin_route._require_admin, None)


def test_admin_exports_blocked_for_non_admin():
    app.dependency_overrides[admin_route._require_admin] = lambda: (_ for _ in ()).throw(HTTPException(status_code=403, detail="forbidden"))
    try:
        response = client.get("/api/v1/admin/exports/list")
        assert response.status_code == 403
    finally:
        app.dependency_overrides.pop(admin_route._require_admin, None)

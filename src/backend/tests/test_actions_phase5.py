from fastapi.testclient import TestClient

from api.routes import actions as actions_route
from core.database import SessionLocal
from core.models import Setting
from main import app


client = TestClient(app)


def _override_auth():
    class _Principal:
        username = "admin"
        role = "admin"
        allowed_teams = []
        allowed_apps = []
        allowed_envs = []
        allowed_compartment_ids = []

        @property
        def is_admin(self):
            return True

    app.dependency_overrides[actions_route._principal] = lambda: _Principal()


def _clear_auth_override():
    app.dependency_overrides.pop(actions_route._principal, None)


def _create_sample_action():
    response = client.post(
        "/api/v1/actions",
        json={
            "source": "manual",
            "category": "notify_only",
            "target_type": "policy",
            "target_ref": {"resource_id": "x-1", "team": "platform"},
            "proposed_change": {"executor_type": "notify_only"},
            "estimated_savings_monthly": 0,
            "confidence": "high",
            "risk_level": "safe",
            "notes": "phase5 test",
        },
    )
    assert response.status_code == 200
    return response.json()["data"]["action_id"]


def test_actions_contracts_and_timeline():
    _override_auth()
    try:
        action_id = _create_sample_action()
        listed = client.get("/api/v1/actions")
        assert listed.status_code == 200
        payload = listed.json()
        assert set(payload.keys()) == {"success", "data"}
        assert "items" in payload["data"]
        row = next(r for r in payload["data"]["items"] if r["action_id"] == action_id)
        assert set(row.keys()) == {
            "action_id",
            "source",
            "category",
            "target_type",
            "target_ref",
            "proposed_change",
            "estimated_savings_monthly",
            "confidence",
            "risk_level",
            "status",
            "requested_by",
            "approved_by",
            "created_at",
            "updated_at",
        }

        detail = client.get(f"/api/v1/actions/{action_id}")
        assert detail.status_code == 200
        detail_data = detail.json()["data"]
        assert set(detail_data.keys()) == {"action", "timeline"}
        assert len(detail_data["timeline"]) >= 1
    finally:
        _clear_auth_override()


def test_action_status_transition_and_idempotency():
    _override_auth()
    try:
        action_id = _create_sample_action()
        run_once = client.post(f"/api/v1/actions/{action_id}/run", json={"dry_run": True})
        assert run_once.status_code == 200
        assert run_once.json()["data"]["status"] == "succeeded"

        run_twice = client.post(f"/api/v1/actions/{action_id}/run", json={"dry_run": True})
        assert run_twice.status_code == 409
    finally:
        _clear_auth_override()


def test_action_approval_required_for_non_safe():
    _override_auth()
    try:
        create = client.post(
            "/api/v1/actions",
            json={
                "source": "manual",
                "category": "cleanup",
                "target_type": "volume",
                "target_ref": {"resource_id": "vol-1"},
                "proposed_change": {"executor_type": "cleanup_unattached_volume"},
                "estimated_savings_monthly": 100,
                "confidence": "medium",
                "risk_level": "moderate",
            },
        )
        assert create.status_code == 200
        action_id = create.json()["data"]["action_id"]

        run_before_approve = client.post(f"/api/v1/actions/{action_id}/run", json={"dry_run": True})
        assert run_before_approve.status_code == 409

        approve = client.post(f"/api/v1/actions/{action_id}/approve", json={"message": "approved for dry-run"})
        assert approve.status_code == 200
        assert approve.json()["data"]["status"] == "approved"

        run_after_approve = client.post(f"/api/v1/actions/{action_id}/run", json={"dry_run": True})
        assert run_after_approve.status_code == 200
    finally:
        _clear_auth_override()


def test_cleanup_executor_requires_confirm_delete_in_live_mode():
    _override_auth()
    try:
        db = SessionLocal()
        s = db.query(Setting).filter(Setting.id == 1).one_or_none()
        if s is None:
            s = Setting(id=1, username="admin", password_hash="x")
            db.add(s)
        s.enable_destructive_actions = True
        db.commit()
        db.close()

        create = client.post(
            "/api/v1/actions",
            json={
                "source": "manual",
                "category": "cleanup",
                "target_type": "volume",
                "target_ref": {"resource_id": "vol-2"},
                "proposed_change": {"executor_type": "cleanup_unattached_volume"},
                "estimated_savings_monthly": 200,
                "confidence": "high",
                "risk_level": "safe",
            },
        )
        action_id = create.json()["data"]["action_id"]
        run_live = client.post(f"/api/v1/actions/{action_id}/run", json={"dry_run": False, "confirm_delete": False})
        assert run_live.status_code == 200
        assert run_live.json()["data"]["status"] == "failed"
    finally:
        _clear_auth_override()

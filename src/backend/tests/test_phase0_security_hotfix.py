from fastapi.testclient import TestClient

from api.routes import admin as admin_route
from core.database import SessionLocal
from core.models import Setting
from main import app
from services.event_logger import redact_sensitive

client = TestClient(app)


def _ensure_settings_row():
    db = SessionLocal()
    try:
        row = db.query(Setting).filter(Setting.id == 1).one_or_none()
        if row is None:
            row = Setting(id=1, username="admin", password_hash="x")
            db.add(row)
        row.oci_key_content = "-----BEGIN PRIVATE KEY-----\nSECRET\n-----END PRIVATE KEY-----"
        row.oci_key_file = "/root/.oci/oci_api_key.pem"
        row.oci_pass_phrase = "super-secret"
        row.oci_config_file = "/root/.oci/config"
        row.oci_fingerprint = "fp-123"
        row.oci_region = "us-phoenix-1"
        db.commit()
    finally:
        db.close()


def test_settings_api_does_not_return_secret_fields():
    _ensure_settings_row()
    app.dependency_overrides[admin_route._require_admin] = lambda: {"sub": "admin"}
    try:
        res = client.get("/api/v1/admin/settings")
        assert res.status_code == 200
        data = res.json()["data"]
        assert "oci_key_content" not in data
        assert "oci_key_file" not in data
        assert "oci_pass_phrase" not in data
        assert "oci_config_file" not in data
        assert data.get("oci_fingerprint") == "fp-123"
        assert data.get("oci_region") == "us-phoenix-1"
    finally:
        app.dependency_overrides.pop(admin_route._require_admin, None)


def test_production_blocks_filesystem_fields(monkeypatch):
    app.dependency_overrides[admin_route._require_admin] = lambda: {"sub": "admin"}
    monkeypatch.setattr(
        admin_route,
        "get_app_settings",
        lambda: type("Cfg", (), {"app_env": "production", "allow_oci_file_path_mode": False})(),
    )
    try:
        res = client.put("/api/v1/admin/settings", json={"oci_key_file": "/root/.oci/oci_api_key.pem"})
        assert res.status_code == 400
        body = res.json()
        err = body.get("detail", {}).get("error") or body.get("error", {})
        assert err.get("code") == "FIELD_BLOCKED_IN_PRODUCTION"
        assert err.get("field") == "oci_key_file"
    finally:
        app.dependency_overrides.pop(admin_route._require_admin, None)


def test_redaction_masks_pem():
    value = {"oci_key_content": "-----BEGIN PRIVATE KEY-----\nSECRET\n-----END PRIVATE KEY-----"}
    redacted = redact_sensitive(value)
    assert redacted["oci_key_content"] == "***REDACTED***" or redacted["oci_key_content"] == "[REDACTED_SECRET]"


def test_correlation_id_header_present_on_errors():
    res = client.get("/api/v1/admin/settings")
    assert res.status_code in (401, 403)
    assert res.headers.get("x-correlation-id")


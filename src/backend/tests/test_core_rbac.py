"""Unit tests for core/rbac.py (role × action permission matrix + scope checks)."""

from __future__ import annotations

import pytest

from core.rbac import (
    Principal,
    can_approve_or_run,
    can_create_action,
    feature_flags,
    has_scope_access,
    principal_from_setting,
    role_job_profile,
)


def _principal(role: str, **scope) -> Principal:
    return Principal(
        username="user",
        role=role,
        allowed_teams=scope.get("teams", []),
        allowed_apps=scope.get("apps", []),
        allowed_envs=scope.get("envs", []),
        allowed_compartment_ids=scope.get("compartments", []),
    )


# ---------------------------------------------------------------------------
# can_create_action — only roles other than viewer should create actions
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("role,expected", [
    ("admin", True),
    ("finops", True),
    ("engineer", True),
    ("viewer", False),
    ("unknown_role", False),
])
def test_can_create_action_matrix(role, expected):
    assert can_create_action(_principal(role)) is expected


# ---------------------------------------------------------------------------
# can_approve_or_run — admin → all risk levels, finops → safe only, others → none
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("role,risk,expected", [
    ("admin", "safe", True),
    ("admin", "moderate", True),
    ("admin", "destructive", True),
    ("finops", "safe", True),
    ("finops", "moderate", False),
    ("finops", "destructive", False),
    ("engineer", "safe", False),
    ("engineer", "moderate", False),
    ("viewer", "safe", False),
])
def test_can_approve_or_run_matrix(role, risk, expected):
    assert can_approve_or_run(_principal(role), risk) is expected


# ---------------------------------------------------------------------------
# has_scope_access — admin bypasses; non-admin enforces each allow-list
# ---------------------------------------------------------------------------

def test_admin_has_unrestricted_scope_access():
    admin = _principal("admin")
    assert has_scope_access(admin, team="platform", app="ledger", env="prod", compartment_id="c-1")


def test_non_admin_with_empty_scopes_is_unrestricted():
    """Empty allow-list means 'not restricted on this dimension'."""
    p = _principal("finops")
    assert has_scope_access(p, team="t1", app="a1", env="prod", compartment_id="c-1") is True


def test_team_scope_blocks_outsiders():
    p = _principal("finops", teams=["platform"])
    assert has_scope_access(p, team="platform") is True
    assert has_scope_access(p, team="other") is False


def test_app_scope_blocks_outsiders():
    p = _principal("engineer", apps=["ledger"])
    assert has_scope_access(p, app="ledger") is True
    assert has_scope_access(p, app="other") is False


def test_env_scope_blocks_outsiders():
    p = _principal("viewer", envs=["prod"])
    assert has_scope_access(p, env="prod") is True
    assert has_scope_access(p, env="dev") is False


def test_compartment_scope_blocks_outsiders():
    p = _principal("engineer", compartments=["c-1"])
    assert has_scope_access(p, compartment_id="c-1") is True
    assert has_scope_access(p, compartment_id="c-2") is False


def test_scope_check_skips_dimensions_not_passed():
    """If the caller passes None for a dimension, that dimension shouldn't deny access."""
    p = _principal("finops", teams=["platform"], envs=["prod"])
    # asking about app/compartment only — team/env not passed should not block
    assert has_scope_access(p, app=None, compartment_id=None) is True


# ---------------------------------------------------------------------------
# role_job_profile — known roles return their profile, unknown defaults to viewer
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("role", ["admin", "finops", "engineer", "viewer"])
def test_role_job_profile_returns_expected_role(role):
    profile = role_job_profile(role)
    assert "title" in profile and "permissions" in profile


def test_role_job_profile_falls_back_to_viewer_for_unknown():
    profile = role_job_profile("nonexistent")
    viewer = role_job_profile("viewer")
    assert profile == viewer


def test_role_job_profile_handles_none_input():
    assert role_job_profile(None) == role_job_profile("viewer")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# principal_from_setting — None setting yields admin default
# ---------------------------------------------------------------------------

def test_principal_from_setting_none_defaults_admin():
    p = principal_from_setting(None)
    assert p.is_admin is True
    assert p.username == "admin"
    assert p.allowed_teams == []


def test_principal_from_setting_uses_setting_values():
    class _Setting:
        username = "owner"
        user_role = "FINOPS"  # case-insensitive
        allowed_teams = ["platform"]
        allowed_apps = ["ledger"]
        allowed_envs = ["prod"]
        allowed_compartment_ids = ["c-1"]

    p = principal_from_setting(_Setting())
    assert p.is_admin is False
    assert p.role == "finops"
    assert p.username == "owner"
    assert p.allowed_teams == ["platform"]


# ---------------------------------------------------------------------------
# feature_flags — None setting returns sensible defaults
# ---------------------------------------------------------------------------

def test_feature_flags_with_none_setting_returns_defaults():
    flags = feature_flags(None)
    expected_keys = {
        "enable_oci_executors",
        "enable_destructive_actions",
        "enable_notifications",
        "enable_budget_auto_eval",
        "enable_demo_mode",
    }
    assert set(flags.keys()) == expected_keys
    assert flags["enable_oci_executors"] is False
    assert flags["enable_destructive_actions"] is False
    assert flags["enable_budget_auto_eval"] is True  # default-on for autoscan


def test_feature_flags_reflects_setting_values():
    class _Setting:
        enable_oci_executors = True
        enable_destructive_actions = False
        notifications_email_enabled = True
        notifications_webhook_enabled = False
        enable_budget_auto_eval = False
        enable_demo_mode = True

    flags = feature_flags(_Setting())
    assert flags["enable_oci_executors"] is True
    assert flags["enable_notifications"] is True
    assert flags["enable_budget_auto_eval"] is False
    assert flags["enable_demo_mode"] is True

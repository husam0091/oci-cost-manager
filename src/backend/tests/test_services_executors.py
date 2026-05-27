"""Unit tests for the local (non-OCI) executors in services/executors/*.

These executors are safety-critical: they gate destructive operations behind
``dry_run`` and ``confirm_delete`` flags. Tests pin those gates explicitly.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from services.executors import (
    cleanup_unattached_volume,
    notify_only,
    stop_idle_instance,
    tag_fix,
)


# ---------------------------------------------------------------------------
# stop_idle_instance
# ---------------------------------------------------------------------------

def test_stop_idle_dry_run_reports_what_it_would_do():
    result = stop_idle_instance.execute(target_ref={"resource_id": "vm-1"}, dry_run=True)
    assert result["ok"] is True
    assert result["dry_run"] is True
    assert result["rollback_supported"] is True
    assert "vm-1" in result["message"]
    assert "would stop" in result["message"].lower()


def test_stop_idle_simulated_live_run():
    result = stop_idle_instance.execute(target_ref={"resource_id": "vm-1"}, dry_run=False)
    assert result["ok"] is True
    assert result["dry_run"] is False
    assert "simulated" in result["message"].lower()


def test_stop_idle_falls_back_when_target_missing():
    """A missing resource id must not raise — falls back to 'unknown'."""
    result = stop_idle_instance.execute(target_ref={}, dry_run=True)
    assert result["ok"] is True
    assert "unknown" in result["message"]


def test_stop_idle_rollback_starts_instance():
    result = stop_idle_instance.rollback(target_ref={"ocid": "vm-1"}, dry_run=False)
    assert result["ok"] is True
    assert "started" in result["message"].lower()


# ---------------------------------------------------------------------------
# cleanup_unattached_volume — confirm_delete gate is the safety net
# ---------------------------------------------------------------------------

def test_cleanup_dry_run_is_always_safe():
    result = cleanup_unattached_volume.execute(
        target_ref={"resource_id": "vol-1"},
        proposed_change={"size_gb": 50},
        dry_run=True,
        confirm_delete=False,
    )
    assert result["ok"] is True
    assert result["dry_run"] is True
    assert result["rollback_supported"] is False  # deletion is not reversible


def test_cleanup_live_run_without_confirm_is_blocked():
    """Without confirm_delete=True the executor must refuse to delete — even in live mode."""
    result = cleanup_unattached_volume.execute(
        target_ref={"resource_id": "vol-1"},
        proposed_change={},
        dry_run=False,
        confirm_delete=False,
    )
    assert result["ok"] is False
    assert "confirm_delete" in result["message"]


def test_cleanup_live_run_with_confirm_proceeds():
    result = cleanup_unattached_volume.execute(
        target_ref={"resource_id": "vol-1"},
        proposed_change={"size_gb": 50},
        dry_run=False,
        confirm_delete=True,
    )
    assert result["ok"] is True
    assert result["dry_run"] is False
    assert result["rollback_supported"] is False
    assert result.get("proposed_change") == {"size_gb": 50}


# ---------------------------------------------------------------------------
# tag_fix — operates against the DB; uses an in-memory fake session
# ---------------------------------------------------------------------------

class _FakeQuery:
    def __init__(self, resource):
        self.resource = resource

    def filter(self, *_args, **_kwargs):
        return self

    def one_or_none(self):
        return self.resource


class _FakeSession:
    def __init__(self, resource):
        self.resource = resource
        self.added = []

    def query(self, _model):
        return _FakeQuery(self.resource)

    def add(self, obj):
        self.added.append(obj)


def _make_resource(tags: dict | None = None):
    return SimpleNamespace(
        ocid="vol-tag-1",
        details={"freeform_tags": dict(tags or {})},
    )


def test_tag_fix_requires_target_id():
    db = _FakeSession(_make_resource())
    out = tag_fix.execute(db=db, target_ref={}, proposed_change={"tags": {"team": "x"}}, dry_run=True)
    assert out["ok"] is False
    assert "target_ref.resource_id" in out["message"]


def test_tag_fix_returns_not_found_when_resource_missing():
    db = _FakeSession(resource=None)
    out = tag_fix.execute(db=db, target_ref={"resource_id": "missing"}, proposed_change={"tags": {}}, dry_run=True)
    assert out["ok"] is False
    assert "not found" in out["message"].lower()


def test_tag_fix_dry_run_does_not_write_but_returns_diff():
    res = _make_resource(tags={"team": "old"})
    db = _FakeSession(res)
    out = tag_fix.execute(
        db=db,
        target_ref={"resource_id": "vol-tag-1"},
        proposed_change={"tags": {"team": "new", "env": "prod"}},
        dry_run=True,
    )
    assert out["ok"] is True
    assert out["dry_run"] is True
    assert out["before_tags"] == {"team": "old"}
    assert out["after_tags"] == {"team": "new", "env": "prod"}
    # No DB write occurred
    assert db.added == []
    assert res.details["freeform_tags"] == {"team": "old"}


def test_tag_fix_live_run_merges_into_resource_details():
    res = _make_resource(tags={"team": "old"})
    db = _FakeSession(res)
    out = tag_fix.execute(
        db=db,
        target_ref={"resource_id": "vol-tag-1"},
        proposed_change={"tags": {"env": "prod"}},
        dry_run=False,
    )
    assert out["ok"] is True
    assert out["dry_run"] is False
    assert res.details["freeform_tags"] == {"team": "old", "env": "prod"}
    assert db.added == [res]


def test_tag_fix_rollback_restores_payload_tags():
    res = _make_resource(tags={"team": "new", "env": "prod"})
    db = _FakeSession(res)
    out = tag_fix.rollback(
        db=db,
        target_ref={"resource_id": "vol-tag-1"},
        payload={"before_tags": {"team": "old"}},
        dry_run=False,
    )
    assert out["ok"] is True
    assert res.details["freeform_tags"] == {"team": "old"}


def test_tag_fix_rollback_dry_run_does_not_mutate():
    res = _make_resource(tags={"team": "new"})
    db = _FakeSession(res)
    tag_fix.rollback(
        db=db,
        target_ref={"resource_id": "vol-tag-1"},
        payload={"before_tags": {"team": "old"}},
        dry_run=True,
    )
    assert res.details["freeform_tags"] == {"team": "new"}


# ---------------------------------------------------------------------------
# notify_only — never supports rollback; calls send_notifications in live mode
# ---------------------------------------------------------------------------

def test_notify_only_dry_run_does_not_send():
    out = notify_only.execute(
        payload={"subject": "x"},
        email_cfg={},
        webhook_cfg={},
        dry_run=True,
    )
    assert out["ok"] is True
    assert out["dry_run"] is True
    assert out["rollback_supported"] is False


def test_notify_only_live_run_invokes_send_notifications(monkeypatch):
    captured = {}

    def fake_send(*, payload, email_cfg, webhook_cfg):
        captured["payload"] = payload
        captured["email_cfg"] = email_cfg
        captured["webhook_cfg"] = webhook_cfg
        return {"emails_sent": 1}

    monkeypatch.setattr("services.executors.notify_only.send_notifications", fake_send)

    out = notify_only.execute(
        payload={"subject": "Budget alert"},
        email_cfg={"smtp_host": "mail"},
        webhook_cfg={"url": "https://x"},
        dry_run=False,
    )
    assert out["ok"] is True
    assert out["result"] == {"emails_sent": 1}
    assert captured["payload"]["subject"] == "Budget alert"


def test_notify_only_rollback_is_unsupported():
    out = notify_only.rollback()
    assert out["ok"] is False
    assert "rollback" in out["message"].lower()

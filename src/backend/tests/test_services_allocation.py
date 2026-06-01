"""Unit tests for services/allocation.py — beyond the single governance route case."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from services.allocation import evaluate_allocation


def _rule(rid: int, name: str, match_type: str, expression: str, *, set_env=None, set_team=None, set_app=None, priority: int = 100, enabled: bool = True):
    return SimpleNamespace(
        id=rid,
        name=name,
        match_type=match_type,
        match_expression=expression,
        set_env=set_env,
        set_team=set_team,
        set_app=set_app,
        priority=priority,
        is_enabled=enabled,
    )


def _resource(name=None, compartment_id=None, details=None):
    return SimpleNamespace(name=name, compartment_id=compartment_id, details=details or {})


# ---------------------------------------------------------------------------
# Tag-first short-circuit: tags filling all three dims → high confidence, no rule.
# ---------------------------------------------------------------------------

def test_tags_filling_all_dims_yield_high_confidence():
    res = _resource(name="api", details={
        "freeform_tags": {"environment": "prod", "owner_team": "platform", "application": "ledger"},
    })
    result = evaluate_allocation(res, rules=[])
    assert result.allocation_confidence == "high"
    assert result.allocation_reason == "tag_keys_env_team_app"
    assert result.env == "prod"
    assert result.team == "platform"
    assert result.app == "ledger"


def test_tag_fallback_keys_env_team_app_short_keys():
    """The shorter alias keys (env/team/app) should be recognized too."""
    res = _resource(details={"freeform_tags": {"env": "stage", "team": "infra", "app": "billing"}})
    result = evaluate_allocation(res, rules=[])
    assert result.allocation_confidence == "high"
    assert result.env == "stage"
    assert result.team == "infra"
    assert result.app == "billing"


# ---------------------------------------------------------------------------
# Rule matching — priority order, rule overrides
# ---------------------------------------------------------------------------

def test_rule_match_on_resource_name_fills_missing_dims():
    res = _resource(name="prod-ledger-vm")
    rules = [
        _rule(1, "tag-prod-ledger", "resource_name", r"prod-ledger", set_env="prod", set_team="platform", set_app="ledger", priority=10),
    ]
    result = evaluate_allocation(res, rules=rules)
    assert result.env == "prod"
    assert result.team == "platform"
    assert result.app == "ledger"
    assert result.allocation_confidence == "medium"
    assert result.allocation_reason.startswith("rule:1:")


def test_rule_priority_lowest_number_runs_first():
    """Lower priority number is processed first; once all dims set, loop breaks."""
    res = _resource(name="api-payments")
    rules = [
        _rule(2, "fallback", "resource_name", r"api", set_env="dev", set_team="infra", set_app="api", priority=100),
        _rule(1, "specific", "resource_name", r"payments", set_env="prod", set_team="payments", set_app="payments", priority=1),
    ]
    result = evaluate_allocation(res, rules=rules)
    assert result.env == "prod"
    assert result.team == "payments"
    assert result.app == "payments"
    # rule with id=1 should win because priority 1 runs first
    assert ":1:" in result.allocation_reason


def test_disabled_rule_is_skipped():
    res = _resource(name="api-payments")
    rules = [
        _rule(1, "disabled", "resource_name", r"payments", set_env="prod", set_team="t", set_app="a", enabled=False),
    ]
    result = evaluate_allocation(res, rules=rules)
    assert result.allocation_confidence == "low"
    assert result.allocation_reason == "no_match"


def test_tag_rule_matches_key_equals_value_pattern():
    res = _resource(details={"freeform_tags": {"costcenter": "ENG-101"}})
    rules = [
        _rule(1, "by-costcenter", "tag", "costcenter=ENG-1.*", set_env="prod", set_team="eng", set_app="core"),
    ]
    result = evaluate_allocation(res, rules=rules)
    assert result.env == "prod"
    assert result.team == "eng"
    assert result.app == "core"


def test_invalid_regex_in_rule_does_not_crash():
    """A rule with malformed regex should simply not match."""
    res = _resource(name="foo")
    rules = [_rule(1, "bad-regex", "resource_name", r"(unclosed", set_env="x")]
    result = evaluate_allocation(res, rules=rules)
    assert result.allocation_confidence == "low"


def test_no_rules_and_no_tags_returns_unallocated_low_confidence():
    res = _resource(name="bare", details={})
    result = evaluate_allocation(res, rules=[])
    assert result.env == "Unallocated"
    assert result.team == "Unallocated"
    assert result.app == "Unallocated"
    assert result.allocation_confidence == "low"
    assert result.allocation_reason == "no_match"


def test_sku_match_type_uses_sku_text_argument():
    res = _resource(name="vm-1")
    rules = [_rule(1, "win-license", "sku", r"Windows OS", set_env="prod", set_team="t", set_app="a")]
    result = evaluate_allocation(res, rules=rules, sku_text="Windows OS - Datacenter")
    assert result.env == "prod"


def test_partial_tag_completion_reaches_medium_confidence():
    """If tags supply two dims and a rule fills the third, confidence is medium."""
    res = _resource(name="ledger-vm-1", details={"freeform_tags": {"environment": "prod", "owner_team": "platform"}})
    rules = [_rule(1, "ledger-app", "resource_name", "ledger", set_app="ledger")]
    result = evaluate_allocation(res, rules=rules)
    assert result.env == "prod"
    assert result.team == "platform"
    assert result.app == "ledger"
    assert result.allocation_confidence == "medium"

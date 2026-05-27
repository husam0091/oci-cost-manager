"""Unit tests for the pure helpers in services/budget_engine.py."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from services.budget_engine import (
    BudgetStatusEval,
    _budget_scope_match,
    _descendants,
    _evaluate_threshold_crossing,
    _explanation,
    _guess_service_name,
    _month_start,
    _next_month_start,
    _safe_pct,
)


# ---------------------------------------------------------------------------
# _safe_pct — must never raise on a zero base.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("value,base,expected", [
    (50.0, 100.0, 50.0),
    (100.0, 100.0, 100.0),
    (0.0, 100.0, 0.0),
    (10.0, 0.0, 0.0),
    (-10.0, 100.0, -10.0),
])
def test_safe_pct(value, base, expected):
    assert _safe_pct(value, base) == pytest.approx(expected)


# ---------------------------------------------------------------------------
# _month_start / _next_month_start
# ---------------------------------------------------------------------------

def test_month_start_zeroes_time_and_day():
    dt = datetime(2026, 5, 14, 13, 27, 45, 123, tzinfo=UTC)
    assert _month_start(dt) == datetime(2026, 5, 1, 0, 0, 0, tzinfo=UTC)


def test_next_month_start_wraps_year_on_december():
    dt = datetime(2026, 12, 20, tzinfo=UTC)
    assert _next_month_start(dt) == datetime(2027, 1, 1, tzinfo=UTC)


def test_next_month_start_normal_case():
    dt = datetime(2026, 3, 10, tzinfo=UTC)
    assert _next_month_start(dt) == datetime(2026, 4, 1, tzinfo=UTC)


def test_next_month_start_is_idempotent_for_first_of_month():
    dt = datetime(2026, 6, 1, tzinfo=UTC)
    assert _next_month_start(dt) == datetime(2026, 7, 1, tzinfo=UTC)


# ---------------------------------------------------------------------------
# _descendants — compartment tree traversal
# ---------------------------------------------------------------------------

def _comp(cid: str, parent: str | None = None):
    return SimpleNamespace(id=cid, parent_id=parent)


def test_descendants_includes_self_and_recursive_children():
    tree = [
        _comp("root"),
        _comp("a", parent="root"),
        _comp("b", parent="root"),
        _comp("a-1", parent="a"),
        _comp("a-1-1", parent="a-1"),
        _comp("orphan"),
    ]
    out = _descendants({"a"}, tree)
    assert out == {"a", "a-1", "a-1-1"}


def test_descendants_with_no_children_is_just_self():
    tree = [_comp("solo")]
    assert _descendants({"solo"}, tree) == {"solo"}


def test_descendants_with_empty_selection_is_empty():
    tree = [_comp("a"), _comp("b", parent="a")]
    assert _descendants(set(), tree) == set()


def test_descendants_does_not_loop_on_cycles():
    """A malformed cycle (a→b, b→a) must terminate."""
    cyclical = [_comp("a", parent="b"), _comp("b", parent="a")]
    out = _descendants({"a"}, cyclical)
    assert out == {"a", "b"}  # both visited once, no infinite loop


# ---------------------------------------------------------------------------
# _budget_scope_match — scope_type fan-out
# ---------------------------------------------------------------------------

def _budget(scope_type: str, scope_value: str = ""):
    return SimpleNamespace(scope_type=scope_type, scope_value=scope_value)


def test_scope_global_matches_everything():
    assert _budget_scope_match(
        _budget("global"),
        row={},
        resource=None,
        alloc_env="prod",
        alloc_team="any",
        alloc_app="any",
        compartment_scope=set(),
    ) is True


def test_scope_team_matches_by_allocation():
    b = _budget("team", "platform")
    assert _budget_scope_match(
        b, row={}, resource=None, alloc_env="", alloc_team="platform", alloc_app="",
        compartment_scope=set(),
    ) is True
    assert _budget_scope_match(
        b, row={}, resource=None, alloc_env="", alloc_team="other", alloc_app="",
        compartment_scope=set(),
    ) is False


def test_scope_app_and_env_matches_independently():
    assert _budget_scope_match(
        _budget("app", "ledger"),
        row={}, resource=None, alloc_env="", alloc_team="", alloc_app="ledger",
        compartment_scope=set(),
    ) is True
    assert _budget_scope_match(
        _budget("env", "prod"),
        row={}, resource=None, alloc_env="prod", alloc_team="", alloc_app="",
        compartment_scope=set(),
    ) is True


def test_scope_compartment_uses_resource_first_then_row():
    b = _budget("compartment")
    res = SimpleNamespace(compartment_id="c-1")
    assert _budget_scope_match(
        b, row={"compartment_id": "wrong"}, resource=res,
        alloc_env="", alloc_team="", alloc_app="",
        compartment_scope={"c-1"},
    ) is True
    # No resource → falls back to row
    assert _budget_scope_match(
        b, row={"compartment_id": "c-1"}, resource=None,
        alloc_env="", alloc_team="", alloc_app="",
        compartment_scope={"c-1"},
    ) is True
    # Outside scope
    assert _budget_scope_match(
        b, row={"compartment_id": "c-2"}, resource=None,
        alloc_env="", alloc_team="", alloc_app="",
        compartment_scope={"c-1"},
    ) is False


def test_scope_unknown_type_returns_false():
    assert _budget_scope_match(
        _budget("bogus"),
        row={}, resource=None, alloc_env="", alloc_team="", alloc_app="",
        compartment_scope=set(),
    ) is False


# ---------------------------------------------------------------------------
# _explanation
# ---------------------------------------------------------------------------

def test_explanation_critical_above_100():
    txt = _explanation(110.0, 130.0, 1000.0, "critical").lower()
    assert "exceeded" in txt


def test_explanation_critical_forecast_only():
    txt = _explanation(50.0, 150.0, 1000.0, "critical").lower()
    assert "forecast" in txt and "breach" in txt


def test_explanation_warning_and_healthy():
    assert "approaching" in _explanation(85.0, 95.0, 1000.0, "warning").lower()
    assert "healthy" in _explanation(20.0, 50.0, 1000.0, "ok").lower()


# ---------------------------------------------------------------------------
# _evaluate_threshold_crossing — returns the HIGHEST threshold crossed.
# ---------------------------------------------------------------------------

def _status(util: float) -> BudgetStatusEval:
    return BudgetStatusEval(
        budget_id="b1",
        budget_name="b1",
        scope_type="global",
        scope_value="",
        current_spend=0.0,
        budget_limit=100.0,
        utilization_pct=util,
        forecast_end_of_month=0.0,
        breach_level="ok",
        days_remaining=0,
        explanation="",
        latest_threshold_crossed=None,
        narrative="",
    )


def test_threshold_crossing_returns_highest_threshold_below_utilization():
    assert _evaluate_threshold_crossing(_status(85.0), [50, 80, 100]) == 80
    assert _evaluate_threshold_crossing(_status(100.0), [50, 80, 100]) == 100


def test_threshold_crossing_returns_none_when_below_all():
    assert _evaluate_threshold_crossing(_status(10.0), [50, 80, 100]) is None


def test_threshold_crossing_dedupes_and_sorts_thresholds():
    assert _evaluate_threshold_crossing(_status(75.0), [50, 80, 50, 70]) == 70


def test_threshold_crossing_empty_thresholds_is_none():
    assert _evaluate_threshold_crossing(_status(99.9), []) is None


# ---------------------------------------------------------------------------
# _guess_service_name — keyword routing
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("sku,rtype,expected", [
    ("Microsoft SQL Server Enterprise", "compute", "Database"),
    ("Block Volume - Storage", "block_volume", "Storage"),
    ("Volume Backup", "volume_backup", "Storage"),
    ("Load Balancer Standard", "load_balancer", "Network"),
    ("VM.Standard.E5.Flex", "compute", "Compute"),
    ("", "object_storage_bucket", "Storage"),
])
def test_guess_service_name(sku, rtype, expected):
    assert _guess_service_name(sku, rtype) == expected

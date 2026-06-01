"""Unit tests for pure helpers in services/recommendations.py."""

from __future__ import annotations

from datetime import UTC, datetime, timezone
from types import SimpleNamespace

import pytest

from services.recommendations import (
    _confidence_rank,
    _deterministic_id,
    _license_kind,
    _parse_datetime,
    _resource_name,
    _safe_pct,
    _short_ocid,
    _to_item,
)


# ---------------------------------------------------------------------------
# _safe_pct
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("delta,base,expected", [
    (10.0, 100.0, 10.0),
    (-25.0, 100.0, -25.0),
    (5.0, 0.0, 0.0),
    (0.0, 100.0, 0.0),
])
def test_safe_pct(delta, base, expected):
    assert _safe_pct(delta, base) == pytest.approx(expected)


# ---------------------------------------------------------------------------
# _short_ocid — returns last 16 chars of trailing segment
# ---------------------------------------------------------------------------

def test_short_ocid_truncates_to_last_16_chars():
    ocid = "ocid1.instance.oc1.iad.abcdefghijklmnopqrstuvwxyz1234567890"
    out = _short_ocid(ocid)
    assert len(out) == 16
    assert out == "uvwxyz1234567890"


def test_short_ocid_none_and_empty():
    assert _short_ocid(None) == "unknown"
    assert _short_ocid("") == "unknown"


def test_short_ocid_short_input_left_untouched():
    assert _short_ocid("abcd") == "abcd"


# ---------------------------------------------------------------------------
# _confidence_rank — orders high<medium<low<unknown
# ---------------------------------------------------------------------------

def test_confidence_rank_ordering():
    assert _confidence_rank("high") < _confidence_rank("medium") < _confidence_rank("low")
    assert _confidence_rank("low") < _confidence_rank("unknown")


def test_confidence_rank_unknown_falls_back_to_3():
    assert _confidence_rank("xyz") == 3
    assert _confidence_rank("") == 3


# ---------------------------------------------------------------------------
# _deterministic_id — same inputs → same id; different inputs → different id
# ---------------------------------------------------------------------------

def test_deterministic_id_is_stable_across_calls():
    a = _deterministic_id("waste", "unattached", "r-1", "no_attachment")
    b = _deterministic_id("waste", "unattached", "r-1", "no_attachment")
    assert a == b
    assert a.startswith("rec_")
    assert len(a) == len("rec_") + 14


def test_deterministic_id_changes_when_any_field_changes():
    base = _deterministic_id("waste", "unattached", "r-1", "no_attachment")
    assert _deterministic_id("license", "unattached", "r-1", "no_attachment") != base
    assert _deterministic_id("waste", "other", "r-1", "no_attachment") != base
    assert _deterministic_id("waste", "unattached", "r-2", "no_attachment") != base
    assert _deterministic_id("waste", "unattached", "r-1", "other_reason") != base


# ---------------------------------------------------------------------------
# _parse_datetime
# ---------------------------------------------------------------------------

def test_parse_datetime_returns_aware_for_aware_input():
    dt = datetime(2026, 1, 5, 10, 30, tzinfo=UTC)
    parsed = _parse_datetime(dt)
    assert parsed == dt
    assert parsed.tzinfo is not None


def test_parse_datetime_attaches_utc_for_naive_input():
    naive = datetime(2026, 1, 5, 10, 30)
    parsed = _parse_datetime(naive)
    assert parsed is not None
    assert parsed.tzinfo == UTC


def test_parse_datetime_handles_iso_strings():
    parsed = _parse_datetime("2026-01-05T10:30:00Z")
    assert parsed is not None
    assert parsed.year == 2026 and parsed.month == 1
    assert parsed.tzinfo is not None


def test_parse_datetime_handles_iso_offset_strings():
    parsed = _parse_datetime("2026-01-05T10:30:00+02:00")
    assert parsed is not None
    # Should produce a tz-aware value (offset preserved)
    assert parsed.tzinfo is not None


@pytest.mark.parametrize("bad", [None, "", "not-a-date", "2026-13-99"])
def test_parse_datetime_invalid_inputs_return_none(bad):
    assert _parse_datetime(bad) is None


# ---------------------------------------------------------------------------
# _resource_name — name when available else short OCID
# ---------------------------------------------------------------------------

def test_resource_name_prefers_name():
    res = SimpleNamespace(name="api-prod-1")
    assert _resource_name(res, "ocid1.instance.oc1..xxx") == "api-prod-1"


def test_resource_name_falls_back_to_short_ocid_when_name_missing():
    res = SimpleNamespace(name=None)
    out = _resource_name(res, "ocid1.instance.oc1.iad.abcdefghijklmnopqrst")
    assert len(out) <= 16


def test_resource_name_with_no_resource_uses_short_ocid():
    assert _resource_name(None, "ocid1.instance.oc1.iad.abcdefghijklmnopqrst") != "unknown"


# ---------------------------------------------------------------------------
# _license_kind — classifies SKU text + resource attributes
# ---------------------------------------------------------------------------

def test_license_kind_sql_from_sku():
    assert _license_kind(None, "Microsoft SQL Server Enterprise") == "sql"
    assert _license_kind(None, "microsoft sql") == "sql"


def test_license_kind_windows_from_sku():
    assert _license_kind(None, "Windows Server 2022 - Datacenter") == "windows"


def test_license_kind_from_resource_image_name():
    res = SimpleNamespace(details={"image_name": "Windows-Server-2022"}, type="compute.instance")
    assert _license_kind(res, "Compute VM") == "windows"


def test_license_kind_from_resource_type():
    sql = SimpleNamespace(details={}, type="sql_server")
    win = SimpleNamespace(details={}, type="windows_server")
    assert _license_kind(sql, "VM") == "sql"
    assert _license_kind(win, "VM") == "windows"


def test_license_kind_none_when_no_match():
    res = SimpleNamespace(details={}, type="compute.instance")
    assert _license_kind(res, "Block Volume") is None


# ---------------------------------------------------------------------------
# _to_item — clamps negatives, rounds costs, uses deterministic id
# ---------------------------------------------------------------------------

def test_to_item_clamps_negative_cost_and_savings_and_rounds():
    item = _to_item(
        category="waste",
        rec_type="unattached_volume",
        resource_ref="r-1",
        resource_name="vol",
        compartment_id="c-1",
        compartment_name="Comp",
        team="t",
        app="a",
        env="prod",
        current_cost=-3.0,
        estimated_savings=12.345,
        confidence="high",
        reason="no_attachment",
        recommendation="Delete the volume",
        why_flagged=["unattached"],
        next_steps=["confirm"],
        history={"current": 12.0, "previous": 10.0},
    )
    assert item.current_cost == 0.0
    assert item.estimated_savings == 12.35  # rounded to 2 decimals
    assert item.recommendation_id.startswith("rec_")


def test_to_item_uses_no_reason_provided_marker_when_blank():
    item = _to_item(
        category="waste",
        rec_type="x",
        resource_ref="r-1",
        resource_name="r",
        compartment_id=None,
        compartment_name=None,
        team="t",
        app="a",
        env="e",
        current_cost=1.0,
        estimated_savings=0.0,
        confidence="low",
        reason="   ",
        recommendation="",
        why_flagged=[],
        next_steps=[],
        history={},
    )
    assert item.reason == "no_reason_provided"

"""Unit tests for pure helpers in services/aggregate_engine.py."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest

from services.aggregate_engine import (
    DateRange,
    _license_type,
    _resource_cost,
    _to_decimal,
    _waste_type,
    resolve_range,
)


# ---------------------------------------------------------------------------
# resolve_range
# ---------------------------------------------------------------------------

def _patch_today(monkeypatch, year: int, month: int, day: int):
    """Pin ``datetime.now(UTC).date()`` to the given date for resolve_range."""

    class _FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):  # noqa: D401 - matches stdlib signature
            return datetime(year, month, day, tzinfo=tz)

    monkeypatch.setattr("services.aggregate_engine.datetime", _FixedDateTime)


def test_resolve_range_ytd_uses_jan_1_to_today(monkeypatch):
    _patch_today(monkeypatch, 2026, 5, 17)
    r = resolve_range("ytd")
    assert r.start == date(2026, 1, 1)
    assert r.end == date(2026, 5, 17)
    # previous period should mirror the same number of days
    assert (r.end - r.start).days == (r.previous_end - r.previous_start).days
    assert r.previous_end == date(2025, 12, 31)


def test_resolve_range_prev_year_main_window_is_full_prior_calendar_year(monkeypatch):
    """The main window pins to the prior calendar year. The previous window is
    a sliding span of the same length, ending the day before the main start."""
    _patch_today(monkeypatch, 2026, 7, 1)
    r = resolve_range("prev_year")
    assert r.start == date(2025, 1, 1)
    assert r.end == date(2025, 12, 31)
    # 365-day sliding window prior to 2025-01-01
    assert r.previous_end == date(2024, 12, 31)
    assert (r.previous_end - r.previous_start).days == (r.end - r.start).days


def test_resolve_range_default_main_window_is_previous_full_month(monkeypatch):
    """Anything other than ytd/prev_year returns the last completed month for the
    main window, with a sliding span_days previous window."""
    _patch_today(monkeypatch, 2026, 3, 15)
    r = resolve_range("anything")
    assert r.start == date(2026, 2, 1)
    assert r.end == date(2026, 2, 28)  # 2026 is not a leap year
    # previous window is 28 days, ending one day before the main start
    assert r.previous_end == date(2026, 1, 31)
    assert (r.previous_end - r.previous_start).days == (r.end - r.start).days


def test_resolve_range_default_handles_january_rollover(monkeypatch):
    """In January, the prior full month is December of the previous year."""
    _patch_today(monkeypatch, 2026, 1, 10)
    r = resolve_range("default")
    assert r.start == date(2025, 12, 1)
    assert r.end == date(2025, 12, 31)
    assert r.previous_end == date(2025, 11, 30)
    assert (r.previous_end - r.previous_start).days == (r.end - r.start).days


def test_resolve_range_returns_daterange_dataclass(monkeypatch):
    _patch_today(monkeypatch, 2026, 5, 17)
    assert isinstance(resolve_range("ytd"), DateRange)


# ---------------------------------------------------------------------------
# _to_decimal
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("value,expected", [
    (5, Decimal("5")),
    (3.14, Decimal("3.14")),
    ("42.50", Decimal("42.50")),
    (None, Decimal("0")),
    (0, Decimal("0")),
])
def test_to_decimal_normal_inputs(value, expected):
    assert _to_decimal(value) == expected


def test_to_decimal_falls_back_to_zero_for_garbage():
    assert _to_decimal("not-a-number") == Decimal("0")
    assert _to_decimal(object()) == Decimal("0")


# ---------------------------------------------------------------------------
# _resource_cost — pulls first present cost-y key
# ---------------------------------------------------------------------------

def _resource(details: dict | None, **kw):
    return SimpleNamespace(details=details, type=kw.get("type", ""), name=kw.get("name", ""), status=kw.get("status", ""))


def test_resource_cost_uses_first_available_key():
    r = _resource({"monthly_cost": 12.5, "total_cost": 9999})
    assert _resource_cost(r) == Decimal("12.5")


def test_resource_cost_priority_order_falls_through():
    r = _resource({"estimated_monthly_cost": 4.0})
    assert _resource_cost(r) == Decimal("4.0")
    r = _resource({"cost": "7"})
    assert _resource_cost(r) == Decimal("7")


def test_resource_cost_returns_zero_when_no_cost_field():
    r = _resource({"other": 5})
    assert _resource_cost(r) == Decimal("0")
    r2 = _resource(None)
    assert _resource_cost(r2) == Decimal("0")


# ---------------------------------------------------------------------------
# _license_type — SQL > Windows > Oracle classification
# ---------------------------------------------------------------------------

def test_license_type_sql_in_name():
    r = _resource({}, type="compute.instance", name="prod-mssql-01")
    assert _license_type(r) == ("sqlserver", "sql_server_license")


def test_license_type_windows_in_type():
    r = _resource({}, type="windows_server", name="api-1")
    assert _license_type(r) == ("windows", "windows_license")


def test_license_type_oracle_in_name():
    r = _resource({}, type="compute.instance", name="ORACLE-db-1")
    assert _license_type(r) == ("oracle", "oracle_license")


def test_license_type_unrelated_returns_none():
    r = _resource({}, type="compute.instance", name="vm-app")
    assert _license_type(r) is None


# ---------------------------------------------------------------------------
# _waste_type — uses is_attached over lifecycle_state when available
# ---------------------------------------------------------------------------

def test_waste_type_backup_resource():
    r = _resource({}, type="volume_backup", name="b1", status="AVAILABLE")
    assert _waste_type(r) == "backup"


def test_waste_type_volume_attached_state_overrides_status():
    """OCI reports lifecycle_state=AVAILABLE for both attached and detached volumes,
    so the scanner-supplied is_attached flag is authoritative."""
    attached = _resource({"is_attached": True}, type="block_volume", status="AVAILABLE")
    detached = _resource({"is_attached": False}, type="block_volume", status="AVAILABLE")
    assert _waste_type(attached) is None
    assert _waste_type(detached) == "unattached_volume"


def test_waste_type_volume_falls_back_to_lifecycle_when_unset():
    no_flag = _resource({}, type="block_volume", status="DETACHED")
    assert _waste_type(no_flag) == "unattached_volume"
    no_flag_available = _resource({}, type="block_volume", status="AVAILABLE")
    assert _waste_type(no_flag_available) is None


def test_waste_type_unrelated_type_returns_none():
    r = _resource({}, type="compute.instance", status="RUNNING")
    assert _waste_type(r) is None

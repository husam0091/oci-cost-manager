"""Unit tests for pure helpers in services/scanner.py."""

from __future__ import annotations

import pytest

from services.scanner import (
    _detect_image_profile,
    _format_bytes,
    _looks_like_sql_workload,
)


# ---------------------------------------------------------------------------
# _detect_image_profile
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("image,expected_type,expected_vendor", [
    ("Windows-Server-2022-Standard-Edition", "windows_server", "microsoft"),
    ("Microsoft SQL Server 2019 Enterprise on Windows", "sql_server", "microsoft"),
    ("mssql-2019-standard", "sql_server", "microsoft"),
    ("Oracle-Linux-8.10-2026.02.20-0", "compute", None),
    ("FortiGate-VM-7.4.1", "security_appliance", "fortinet"),
    ("PaloAlto-PAN-OS-11.0", "security_appliance", "palo_alto"),
    ("F5-BIG-IP-Virtual-Edition", "security_appliance", "f5"),
])
def test_detect_image_profile_classifications(image, expected_type, expected_vendor):
    out = _detect_image_profile(image)
    assert out["resource_type"] == expected_type
    assert out["image_vendor"] == expected_vendor


def test_detect_image_profile_none_returns_generic():
    out = _detect_image_profile(None)
    assert out == {"resource_type": "compute", "image_family": "generic", "image_vendor": None}


def test_detect_image_profile_empty_string_returns_generic():
    out = _detect_image_profile("")
    assert out["resource_type"] == "compute"


def test_detect_image_profile_sql_takes_priority_over_windows():
    """A SQL-on-Windows image is SQL, not Windows."""
    out = _detect_image_profile("Microsoft-SQL-Server-2022-on-Windows-2022")
    assert out["resource_type"] == "sql_server"


# ---------------------------------------------------------------------------
# _looks_like_sql_workload — must NOT match "mysql" (false-positive avoidance)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("inst,image,expected", [
    ("db-prod", "Microsoft SQL Server 2022", True),
    ("mssql-prod", "Oracle Linux", True),
    ("api", "SQL Server Standard", True),
    ("mysql-1", "Oracle Linux", False),    # mysql must NOT trigger
    ("vm-1", "MySQL 8", False),
    ("api", "Oracle Linux 9", False),
    (None, None, False),
])
def test_looks_like_sql_workload(inst, image, expected):
    assert _looks_like_sql_workload(inst, image) is expected


# ---------------------------------------------------------------------------
# _format_bytes — human-readable size scaling
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("size,expected_unit", [
    (None, None),
    (0, None),                     # 0 falls through the "if not size" check
    (512, "B"),
    (2048, "KB"),
    (1024 * 1024 * 5, "MB"),
    (1024 * 1024 * 1024 * 3, "GB"),
    (1024 * 1024 * 1024 * 1024 * 2, "TB"),
    (1024 ** 6, "PB"),
])
def test_format_bytes_unit_selection(size, expected_unit):
    out = _format_bytes(size)
    if expected_unit is None:
        assert out is None
    else:
        assert out is not None
        assert out.endswith(expected_unit)


def test_format_bytes_includes_one_decimal():
    """Output is always one-decimal precision."""
    out = _format_bytes(1500)
    assert out is not None
    assert "." in out

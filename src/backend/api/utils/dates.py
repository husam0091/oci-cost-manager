"""Centralized date parsing/range helpers for API endpoints."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Optional

from fastapi import HTTPException


def parse_iso_datetime(value: Optional[str], *, is_end: bool, required: bool = True) -> datetime:
    """Parse ISO date/datetime and normalize to UTC.

    Date-only values are interpreted as UTC day boundaries.
    End dates are normalized to exclusive boundary (+1 day) for inclusive semantics.
    """
    if value is None:
        if required:
            raise HTTPException(status_code=422, detail="Date value is required")
        now_utc = datetime.now(UTC)
        if is_end:
            return now_utc
        return now_utc.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    raw = str(value).strip()
    if not raw:
        raise HTTPException(status_code=422, detail="Date value is required")
    try:
        if "T" not in raw:
            dt = datetime.fromisoformat(raw).replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=UTC)
            if is_end:
                dt = dt + timedelta(days=1)
            return dt
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"Invalid ISO date: {value}") from exc
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def parse_required_range(start_date: str, end_date: str) -> tuple[datetime, datetime, int]:
    start = parse_iso_datetime(start_date, is_end=False, required=True)
    end_exclusive = parse_iso_datetime(end_date, is_end=True, required=True)
    if end_exclusive <= start:
        raise HTTPException(status_code=422, detail="end_date must be after start_date")
    return start, end_exclusive, (end_exclusive - start).days


def compute_previous_period(start: datetime, end_exclusive: datetime) -> tuple[datetime, datetime]:
    span = end_exclusive - start
    return start - span, start


def iso_date(value: datetime) -> str:
    return value.astimezone(UTC).date().isoformat()


def preset_range(mode: str, now: Optional[datetime] = None) -> tuple[str, str]:
    """Return inclusive YYYY-MM-DD boundaries for common presets."""
    now_dt = (now or datetime.now(UTC)).astimezone(UTC)
    today = now_dt.date()
    if mode == "prev_month":
        first_of_current = today.replace(day=1)
        last_of_prev = first_of_current - timedelta(days=1)
        first_of_prev = last_of_prev.replace(day=1)
        return first_of_prev.isoformat(), last_of_prev.isoformat()
    if mode == "ytd":
        return today.replace(month=1, day=1).isoformat(), today.isoformat()
    if mode == "prev_year":
        year = today.year - 1
        return f"{year}-01-01", f"{year}-12-31"
    raise ValueError(f"Unsupported preset mode: {mode}")


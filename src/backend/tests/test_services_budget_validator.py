"""Unit tests for services/budget_validator.py — threshold boundary math."""

from __future__ import annotations

import pytest

from services.budget_validator import BudgetStatus, BudgetValidatorService


@pytest.fixture
def validator():
    """A validator whose cost_calculator dependency is irrelevant for these pure tests."""
    v = BudgetValidatorService.__new__(BudgetValidatorService)
    v.cost_calculator = None  # not used by calculate_budget_status
    return v


# calculate_budget_status — three boundaries: 0, 80, 100 percent.
# Implementation: <80=HEALTHY, 80..100 exclusive=WARNING, >=100=EXCEEDED, budget<=0=EXCEEDED.

@pytest.mark.parametrize("budget,actual,status", [
    (100.0, 0.0, BudgetStatus.HEALTHY),
    (100.0, 79.99, BudgetStatus.HEALTHY),
    (100.0, 80.0, BudgetStatus.WARNING),
    (100.0, 99.99, BudgetStatus.WARNING),
    (100.0, 100.0, BudgetStatus.EXCEEDED),
    (100.0, 150.0, BudgetStatus.EXCEEDED),
])
def test_calculate_budget_status_default_threshold(validator, budget, actual, status):
    assert validator.calculate_budget_status(budget, actual) == status


def test_zero_budget_treated_as_exceeded(validator):
    """A non-positive budget should not divide by zero — it must report EXCEEDED."""
    assert validator.calculate_budget_status(0.0, 50.0) == BudgetStatus.EXCEEDED
    assert validator.calculate_budget_status(-5.0, 50.0) == BudgetStatus.EXCEEDED


def test_custom_warning_threshold_shifts_boundary(validator):
    """A 60% warning threshold should flip WARNING earlier."""
    assert validator.calculate_budget_status(100.0, 55.0, warning_threshold=60) == BudgetStatus.HEALTHY
    assert validator.calculate_budget_status(100.0, 60.0, warning_threshold=60) == BudgetStatus.WARNING
    assert validator.calculate_budget_status(100.0, 99.0, warning_threshold=60) == BudgetStatus.WARNING
    assert validator.calculate_budget_status(100.0, 100.0, warning_threshold=60) == BudgetStatus.EXCEEDED


def test_get_budget_recommendations_for_exceeded(validator):
    rec = validator.get_budget_recommendations({
        "status": BudgetStatus.EXCEEDED.value,
        "projected_status": BudgetStatus.EXCEEDED.value,
        "consumption_pct": 120.0,
        "daily_burn_rate": 12.0,
        "days_remaining": 5,
        "actual_amount": 1200.0,
        "breakdown_by_service": {"Compute": 800.0, "Storage": 400.0},
    })
    text = " ".join(rec).lower()
    assert "exceeded" in text
    # Compute is >50% so a service-callout should be present
    assert "compute" in text or "50%" in text


def test_get_budget_recommendations_for_healthy_projected_exceeded(validator):
    rec = validator.get_budget_recommendations({
        "status": BudgetStatus.HEALTHY.value,
        "projected_status": BudgetStatus.EXCEEDED.value,
        "consumption_pct": 40.0,
        "daily_burn_rate": 20.0,
        "days_remaining": 15,
        "actual_amount": 400.0,
        "breakdown_by_service": {},
    })
    assert any("projected" in r.lower() for r in rec)


def test_get_budget_recommendations_for_warning(validator):
    rec = validator.get_budget_recommendations({
        "status": BudgetStatus.WARNING.value,
        "projected_status": BudgetStatus.EXCEEDED.value,
        "consumption_pct": 85.0,
        "daily_burn_rate": 10.0,
        "days_remaining": 5,
        "actual_amount": 850.0,
        "breakdown_by_service": {},
    })
    text = " ".join(rec).lower()
    assert "85" in text or "monitor" in text
    assert "burn" in text or "exceed" in text


def test_get_budget_recommendations_empty_breakdown_is_safe(validator):
    """Should not crash when breakdown is empty."""
    rec = validator.get_budget_recommendations({
        "status": BudgetStatus.HEALTHY.value,
        "projected_status": BudgetStatus.HEALTHY.value,
        "consumption_pct": 10.0,
        "daily_burn_rate": 1.0,
        "days_remaining": 25,
        "actual_amount": 10.0,
        "breakdown_by_service": {},
    })
    # No exception. May or may not include any text.
    assert isinstance(rec, list)

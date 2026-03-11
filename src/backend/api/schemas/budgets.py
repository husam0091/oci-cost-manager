"""Pydantic contracts for budget APIs."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator

ScopeType = Literal["global", "compartment", "team", "app", "env"]
CompareMode = Literal["actual", "forecast"]
BreachLevel = Literal["none", "warning", "critical"]


class BudgetModel(BaseModel):
    budget_id: str
    name: str
    scope_type: ScopeType
    scope_value: str
    include_children: bool = False
    period: Literal["monthly"] = "monthly"
    limit_amount: float
    currency: str = "USD"
    growth_cap_pct: Optional[float] = None
    forecast_guardrail_pct: Optional[float] = None
    alert_thresholds: list[int] = Field(default_factory=lambda: [50, 75, 90, 100])
    compare_mode: CompareMode = "actual"
    enabled: bool = True
    notifications_enabled: bool = False
    owner: str
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    created_at: datetime
    updated_at: datetime


class BudgetCreateUpdateModel(BaseModel):
    name: str
    scope_type: ScopeType
    scope_value: str
    include_children: bool = False
    period: Literal["monthly"] = "monthly"
    limit_amount: float = Field(gt=0)
    currency: str = "USD"
    growth_cap_pct: Optional[float] = Field(default=None, ge=0)
    forecast_guardrail_pct: Optional[float] = Field(default=None, ge=0)
    alert_thresholds: list[int] = Field(default_factory=lambda: [50, 75, 90, 100])
    compare_mode: CompareMode = "actual"
    enabled: bool = True
    notifications_enabled: bool = False
    owner: str
    start_date: Optional[date] = None
    end_date: Optional[date] = None

    @model_validator(mode="after")
    def validate_scope(self) -> "BudgetCreateUpdateModel":
        if self.scope_type == "global":
            self.scope_value = "global"
        if not self.scope_value:
            raise ValueError("scope_value is required")
        cleaned = sorted(set(int(x) for x in self.alert_thresholds))
        self.alert_thresholds = [x for x in cleaned if 1 <= x <= 200]
        if not self.alert_thresholds:
            self.alert_thresholds = [50, 75, 90, 100]
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        return self


class BudgetListResponseModel(BaseModel):
    success: Literal[True]
    data: list[BudgetModel]


class BudgetMutationResponseModel(BaseModel):
    success: Literal[True]
    data: BudgetModel


class BudgetDeleteResponseModel(BaseModel):
    success: Literal[True]


class BudgetStatusItemModel(BaseModel):
    budget_id: str
    budget_name: str
    scope_type: ScopeType
    scope_value: str
    current_spend: float
    budget_limit: float
    utilization_pct: float
    forecast_end_of_month: float
    breach_level: BreachLevel
    days_remaining: int
    explanation: str
    narrative: str
    latest_threshold_crossed: Optional[int] = None


class BudgetHistoryItemModel(BaseModel):
    snapshot_date: str
    current_spend: float
    utilization_pct: float
    forecast_end_of_month: float


class BudgetHistoryResponseModel(BaseModel):
    success: Literal[True]
    data: list[BudgetHistoryItemModel]


class BudgetStatusResponseModel(BaseModel):
    success: Literal[True]
    data: list[BudgetStatusItemModel]

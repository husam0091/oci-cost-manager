"""Pydantic models for dashboard summary contract."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel


class PeriodModel(BaseModel):
    start_date: str
    end_date: str
    days: int


class TotalsModel(BaseModel):
    current: float
    previous: float
    delta_abs: float
    delta_pct: float


class TopDriverModel(BaseModel):
    group: str
    current: float
    previous: float
    share_pct: float
    delta_abs: float
    delta_pct: float


class MoverModel(BaseModel):
    entity_type: str
    entity_name: str
    delta_abs: float
    delta_pct: float


class LicenseItemModel(BaseModel):
    monthly_cost: float
    daily_estimate: float
    delta_abs: float


class LicenseSpotlightModel(BaseModel):
    windows: LicenseItemModel
    sql_server: LicenseItemModel
    oracle_os: LicenseItemModel


class StorageItemModel(BaseModel):
    count: int
    monthly_cost: float


class StorageBackupModel(BaseModel):
    unattached_volumes: StorageItemModel
    backups: StorageItemModel


class MappingHealthModel(BaseModel):
    unallocated_pct: float
    low_confidence_count: int


class FreshnessModel(BaseModel):
    last_scan_at: Optional[str] = None
    last_cost_refresh_at: Optional[str] = None


class SpotlightServiceModel(BaseModel):
    name: str
    current: float
    share_pct: float
    delta_abs: float
    delta_pct: float


class SpotlightTotalsModel(BaseModel):
    current: float
    previous: float
    delta_abs: float
    delta_pct: float


class CoreBusinessSpotlightItemModel(BaseModel):
    compartment_id: str
    compartment_name: str
    include_children: bool
    totals: SpotlightTotalsModel
    top_services: list[SpotlightServiceModel]


class SavingsOpportunitiesModel(BaseModel):
    potential_savings_monthly: float
    high_confidence_savings: float
    recommendation_count: int


class HighestBudgetUtilizationModel(BaseModel):
    budget_id: str
    budget_name: str
    utilization_pct: float


class BudgetHealthModel(BaseModel):
    total_budgets: int
    budgets_at_risk: int
    budgets_breached: int
    highest_utilization_budget: Optional[HighestBudgetUtilizationModel] = None


class ExecutiveSignalsModel(BaseModel):
    run_rate_vs_budget: str
    forecasted_month_end_spend: str
    top_risk_budget: str
    top_cost_driver_this_month: str


class DashboardSummaryData(BaseModel):
    period: PeriodModel
    totals: TotalsModel
    top_driver: TopDriverModel
    biggest_mover: MoverModel
    license_spotlight: LicenseSpotlightModel
    storage_backup: StorageBackupModel
    mapping_health: MappingHealthModel
    freshness: FreshnessModel
    core_business_spotlight: list[CoreBusinessSpotlightItemModel] = []
    savings_opportunities: SavingsOpportunitiesModel
    budget_health: BudgetHealthModel
    executive_signals: ExecutiveSignalsModel


class DashboardSummaryResponse(BaseModel):
    success: Literal[True]
    data: DashboardSummaryData

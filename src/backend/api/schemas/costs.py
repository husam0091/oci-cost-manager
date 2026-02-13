"""Pydantic contracts for aggregated cost endpoints."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel


class AggregationPeriodModel(BaseModel):
    start_date: str
    end_date: str
    days: int


class AggregationTotalsModel(BaseModel):
    current: float
    previous: float


class BreakdownItemModel(BaseModel):
    name: str
    current: float
    previous: float
    delta_abs: float
    delta_pct: float
    share_pct: float


class BreakdownDataModel(BaseModel):
    group_by: Literal["service", "compartment", "env", "team", "app"]
    period: AggregationPeriodModel
    totals: AggregationTotalsModel
    items: list[BreakdownItemModel]
    mapping_health: Optional[dict[str, float]] = None


class CostsBreakdownResponse(BaseModel):
    success: Literal[True]
    data: BreakdownDataModel


class MoversItemModel(BaseModel):
    name: str
    current: float
    previous: float
    delta_abs: float
    delta_pct: float
    type: Optional[str] = None
    compartment_name: Optional[str] = None


class MoversDataModel(BaseModel):
    group_by: Literal["service", "compartment", "resource"]
    period: AggregationPeriodModel
    items: list[MoversItemModel]


class CostsMoversResponse(BaseModel):
    success: Literal[True]
    data: MoversDataModel

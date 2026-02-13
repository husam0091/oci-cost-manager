"""Pydantic contracts for optimization recommendations APIs."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel

RecommendationConfidence = Literal["high", "medium", "low"]
RecommendationGroup = Literal["compute", "storage", "backup", "license"]


class RecommendationPeriodModel(BaseModel):
    start_date: str
    end_date: str
    days: int


class RecommendationCategorySummaryModel(BaseModel):
    category: RecommendationGroup
    count: int
    savings_monthly: float


class RecommendationSummaryTotalsModel(BaseModel):
    potential_savings_monthly: float
    recommendation_count: int
    high_confidence_savings: float


class RecommendationSummaryDataModel(BaseModel):
    period: RecommendationPeriodModel
    totals: RecommendationSummaryTotalsModel
    by_category: list[RecommendationCategorySummaryModel]


class RecommendationSummaryResponseModel(BaseModel):
    success: Literal[True]
    data: RecommendationSummaryDataModel


class RecommendationListItemModel(BaseModel):
    recommendation_id: str
    category: RecommendationGroup
    type: str
    resource_ref: str
    resource_name: str
    compartment_id: Optional[str] = None
    compartment_name: Optional[str] = None
    team: str
    app: str
    env: str
    current_cost: float
    estimated_savings: float
    confidence: RecommendationConfidence
    reason: str
    recommendation: str


class RecommendationListDataModel(BaseModel):
    period: RecommendationPeriodModel
    items: list[RecommendationListItemModel]


class RecommendationListResponseModel(BaseModel):
    success: Literal[True]
    data: RecommendationListDataModel


class RecommendationResourceDataModel(BaseModel):
    recommendation_id: str
    type: str
    category: RecommendationGroup
    resource_ref: str
    resource_name: str
    confidence: RecommendationConfidence
    reason: str
    recommendation: str
    why_flagged: list[str]
    next_steps: list[str]
    cost_history_snapshot: dict


class RecommendationResourceResponseModel(BaseModel):
    success: Literal[True]
    data: RecommendationResourceDataModel


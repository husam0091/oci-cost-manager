"""Pydantic contracts for Phase 5 action APIs."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

ActionSource = Literal["recommendation", "budget_alert", "manual"]
ActionCategory = Literal["cleanup", "resize", "schedule", "tag_fix", "notify_only"]
ActionTargetType = Literal["volume", "instance", "backup", "policy", "tag"]
ActionConfidence = Literal["high", "medium", "low"]
ActionRiskLevel = Literal["safe", "moderate", "high"]
ActionStatus = Literal[
    "draft",
    "pending_approval",
    "approved",
    "rejected",
    "queued",
    "running",
    "succeeded",
    "failed",
    "rolled_back",
]
ActionEventType = Literal["created", "approved", "executed", "failed", "rollback", "comment"]


class ActionRequestModel(BaseModel):
    action_id: str
    source: ActionSource
    category: ActionCategory
    target_type: ActionTargetType
    target_ref: dict[str, Any]
    proposed_change: dict[str, Any]
    estimated_savings_monthly: float
    confidence: ActionConfidence
    risk_level: ActionRiskLevel
    status: ActionStatus
    requested_by: Optional[str] = None
    approved_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ActionEventModel(BaseModel):
    event_type: ActionEventType
    message: Optional[str] = None
    payload: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime


class ActionCreateRequestModel(BaseModel):
    source: ActionSource
    category: ActionCategory
    target_type: ActionTargetType
    target_ref: dict[str, Any] = Field(default_factory=dict)
    proposed_change: dict[str, Any] = Field(default_factory=dict)
    estimated_savings_monthly: float = 0.0
    confidence: ActionConfidence = "low"
    risk_level: ActionRiskLevel = "moderate"
    recommendation_id: Optional[str] = None
    budget_alert_id: Optional[int] = None
    notes: Optional[str] = None


class ActionCreateResponseModel(BaseModel):
    success: Literal[True]
    data: ActionRequestModel


class ActionListDataModel(BaseModel):
    items: list[ActionRequestModel]


class ActionListResponseModel(BaseModel):
    success: Literal[True]
    data: ActionListDataModel


class ActionDetailDataModel(BaseModel):
    action: ActionRequestModel
    timeline: list[ActionEventModel]


class ActionDetailResponseModel(BaseModel):
    success: Literal[True]
    data: ActionDetailDataModel


class ActionDecisionRequestModel(BaseModel):
    message: Optional[str] = None


class ActionRunRequestModel(BaseModel):
    dry_run: bool = True
    confirm_delete: bool = False


class ActionRollbackRequestModel(BaseModel):
    dry_run: bool = True
    message: Optional[str] = None


class ActionOperationResponseModel(BaseModel):
    success: Literal[True]
    data: dict[str, Any]

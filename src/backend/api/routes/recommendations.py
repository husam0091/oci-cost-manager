"""Optimization recommendation endpoints."""

from __future__ import annotations

from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, Cookie, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from api.schemas.recommendations import (
    RecommendationCategorySummaryModel,
    RecommendationListDataModel,
    RecommendationListItemModel,
    RecommendationListResponseModel,
    RecommendationPeriodModel,
    RecommendationResourceDataModel,
    RecommendationResourceResponseModel,
    RecommendationSummaryDataModel,
    RecommendationSummaryResponseModel,
    RecommendationSummaryTotalsModel,
)
from api.utils.dates import iso_date, parse_required_range
from core.cache import get_cached, set_cached
from core.database import get_db
from core.rbac import has_scope_access, resolve_principal
from services.recommendations import generate_recommendations

router = APIRouter()
RECOMMENDATIONS_CACHE_TTL = 90


def _summary_cache_key(start_date: str, end_date: str) -> str:
    return f"recs_summary|start={start_date}|end={end_date}"


def _list_cache_key(start_date: str, end_date: str) -> str:
    return f"recs_list|start={start_date}|end={end_date}"


@router.get("/recommendations/summary", response_model=RecommendationSummaryResponseModel)
async def recommendations_summary(
    start_date: str = Query(...),
    end_date: str = Query(...),
    token: Optional[str] = Cookie(default=None, alias="access_token"),
    db: Session = Depends(get_db),
):
    start, end_exclusive, days = parse_required_range(start_date, end_date)
    normalized_start = iso_date(start)
    normalized_end = iso_date(end_exclusive - timedelta(days=1))
    cached = get_cached(_summary_cache_key(normalized_start, normalized_end))
    if cached is not None:
        return RecommendationSummaryResponseModel(**cached)

    payload = generate_recommendations(db=db, start=start, end_exclusive=end_exclusive)
    principal = resolve_principal(db, token, strict=False)
    items = [
        i
        for i in payload["items"]
        if has_scope_access(
            principal,
            team=getattr(i, "team", None),
            app=getattr(i, "app", None),
            env=getattr(i, "env", None),
            compartment_id=getattr(i, "compartment_id", None),
        )
    ]
    by_category: dict[str, dict[str, float]] = {}
    for item in items:
        slot = by_category.setdefault(item.category, {"count": 0, "savings_monthly": 0.0})
        slot["count"] += 1
        slot["savings_monthly"] += item.estimated_savings

    summary = RecommendationSummaryResponseModel(
        success=True,
        data=RecommendationSummaryDataModel(
            period=RecommendationPeriodModel(
                start_date=normalized_start,
                end_date=normalized_end,
                days=days,
            ),
            totals=RecommendationSummaryTotalsModel(
                potential_savings_monthly=round(sum(i.estimated_savings for i in items), 2),
                recommendation_count=len(items),
                high_confidence_savings=round(sum(i.estimated_savings for i in items if i.confidence == "high"), 2),
            ),
            by_category=[
                RecommendationCategorySummaryModel(
                    category=category,  # type: ignore[arg-type]
                    count=int(vals["count"]),
                    savings_monthly=round(float(vals["savings_monthly"]), 2),
                )
                for category, vals in sorted(by_category.items(), key=lambda kv: kv[0])
            ],
        ),
    )
    set_cached(_summary_cache_key(normalized_start, normalized_end), summary.model_dump(), RECOMMENDATIONS_CACHE_TTL)
    return summary


@router.get("/recommendations/list", response_model=RecommendationListResponseModel)
async def recommendations_list(
    start_date: str = Query(...),
    end_date: str = Query(...),
    category: Optional[str] = Query(None),
    confidence: Optional[str] = Query(None),
    compartment_id: Optional[str] = Query(None),
    team: Optional[str] = Query(None),
    app: Optional[str] = Query(None),
    env: Optional[str] = Query(None),
    token: Optional[str] = Cookie(default=None, alias="access_token"),
    db: Session = Depends(get_db),
):
    start, end_exclusive, days = parse_required_range(start_date, end_date)
    normalized_start = iso_date(start)
    normalized_end = iso_date(end_exclusive - timedelta(days=1))
    cached = get_cached(_list_cache_key(normalized_start, normalized_end))
    if cached is not None:
        base = RecommendationListResponseModel(**cached)
        items = base.data.items
    else:
        payload = generate_recommendations(db=db, start=start, end_exclusive=end_exclusive)
        items = [
            RecommendationListItemModel(
                recommendation_id=i.recommendation_id,
                category=i.category,  # type: ignore[arg-type]
                type=i.type,
                resource_ref=i.resource_ref,
                resource_name=i.resource_name,
                compartment_id=i.compartment_id,
                compartment_name=i.compartment_name,
                team=i.team,
                app=i.app,
                env=i.env,
                current_cost=i.current_cost,
                estimated_savings=i.estimated_savings,
                confidence=i.confidence,  # type: ignore[arg-type]
                reason=i.reason,
                recommendation=i.recommendation,
            )
            for i in payload["items"]
        ]
        model = RecommendationListResponseModel(
            success=True,
            data=RecommendationListDataModel(
                period=RecommendationPeriodModel(
                    start_date=normalized_start,
                    end_date=normalized_end,
                    days=days,
                ),
                items=items,
            ),
        )
        set_cached(_list_cache_key(normalized_start, normalized_end), model.model_dump(), RECOMMENDATIONS_CACHE_TTL)

    principal = resolve_principal(db, token, strict=False)
    filtered = []
    for item in items:
        if category and item.category != category:
            continue
        if confidence and item.confidence != confidence:
            continue
        if compartment_id and item.compartment_id != compartment_id:
            continue
        if team and item.team != team:
            continue
        if app and item.app != app:
            continue
        if env and item.env != env:
            continue
        if not has_scope_access(
            principal,
            team=item.team,
            app=item.app,
            env=item.env,
            compartment_id=item.compartment_id,
        ):
            continue
        filtered.append(item)

    return RecommendationListResponseModel(
        success=True,
        data=RecommendationListDataModel(
            period=RecommendationPeriodModel(
                start_date=normalized_start,
                end_date=normalized_end,
                days=days,
            ),
            items=filtered,
        ),
    )


@router.get("/recommendations/resource/{recommendation_id}", response_model=RecommendationResourceResponseModel)
async def recommendation_by_id(
    recommendation_id: str,
    start_date: str = Query(...),
    end_date: str = Query(...),
    token: Optional[str] = Cookie(default=None, alias="access_token"),
    db: Session = Depends(get_db),
):
    start, end_exclusive, _days = parse_required_range(start_date, end_date)
    payload = generate_recommendations(db=db, start=start, end_exclusive=end_exclusive)
    match = next((i for i in payload["items"] if i.recommendation_id == recommendation_id), None)
    if not match:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    principal = resolve_principal(db, token, strict=False)
    if not has_scope_access(
        principal,
        team=getattr(match, "team", None),
        app=getattr(match, "app", None),
        env=getattr(match, "env", None),
        compartment_id=getattr(match, "compartment_id", None),
    ):
        raise HTTPException(status_code=404, detail="Recommendation not found")

    return RecommendationResourceResponseModel(
        success=True,
        data=RecommendationResourceDataModel(
            recommendation_id=match.recommendation_id,
            type=match.type,
            category=match.category,  # type: ignore[arg-type]
            resource_ref=match.resource_ref,
            resource_name=match.resource_name,
            confidence=match.confidence,  # type: ignore[arg-type]
            reason=match.reason,
            recommendation=match.recommendation,
            why_flagged=match.why_flagged,
            next_steps=match.next_steps,
            cost_history_snapshot=match.history,
        ),
    )

"""Insights API alias endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from core.database import get_db
from .costs import get_insights as get_cost_insights

router = APIRouter()


@router.get("")
async def get_insights(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Alias for governance insights at /api/v1/insights."""
    return await get_cost_insights(start_date=start_date, end_date=end_date, db=db)


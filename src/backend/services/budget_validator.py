"""Budget validation service for comparing budgets vs actual costs."""

from datetime import UTC, datetime, date
from typing import Optional, Dict, Any, List
from enum import Enum
from decimal import Decimal

from .cost_calculator import get_cost_calculator


class BudgetStatus(str, Enum):
    """Budget health status."""
    HEALTHY = "healthy"      # < 80% consumed
    WARNING = "warning"      # 80-100% consumed
    EXCEEDED = "exceeded"    # > 100% consumed


class BudgetValidatorService:
    """Service for validating budgets against actual costs."""
    
    def __init__(self):
        """Initialize budget validator service."""
        self.cost_calculator = get_cost_calculator()
    
    def calculate_budget_status(
        self,
        budget_amount: float,
        actual_amount: float,
        warning_threshold: int = 80,
    ) -> BudgetStatus:
        """Calculate budget status based on consumption.
        
        Args:
            budget_amount: Total budget amount.
            actual_amount: Actual spent amount.
            warning_threshold: Percentage threshold for warning status.
            
        Returns:
            BudgetStatus enum value.
        """
        if budget_amount <= 0:
            return BudgetStatus.EXCEEDED
        
        consumption_pct = (actual_amount / budget_amount) * 100
        
        if consumption_pct >= 100:
            return BudgetStatus.EXCEEDED
        elif consumption_pct >= warning_threshold:
            return BudgetStatus.WARNING
        else:
            return BudgetStatus.HEALTHY
    
    def validate_budget(
        self,
        budget_amount: float,
        period_type: str,  # "monthly" or "yearly"
        start_date: Optional[date] = None,
        compartment_id: Optional[str] = None,
        warning_threshold: int = 80,
    ) -> Dict[str, Any]:
        """Validate a budget against actual costs.
        
        Args:
            budget_amount: Budget amount.
            period_type: "monthly" or "yearly".
            start_date: Start of budget period. Defaults to current month/year.
            compartment_id: Optional compartment to scope the budget.
            warning_threshold: Percentage for warning status.
            
        Returns:
            Dictionary with validation results.
        """
        today = datetime.now(UTC)
        
        # Determine period boundaries
        if period_type == "monthly":
            if start_date:
                period_start = datetime.combine(start_date, datetime.min.time())
            else:
                period_start = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            
            # End of month
            if period_start.month == 12:
                period_end = period_start.replace(year=period_start.year + 1, month=1)
            else:
                period_end = period_start.replace(month=period_start.month + 1)
            
            days_in_period = (period_end - period_start).days
            days_elapsed = min((today - period_start).days + 1, days_in_period)
        else:  # yearly
            if start_date:
                period_start = datetime.combine(start_date, datetime.min.time())
            else:
                period_start = today.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            
            period_end = period_start.replace(year=period_start.year + 1)
            days_in_period = (period_end - period_start).days
            days_elapsed = min((today - period_start).days + 1, days_in_period)
        
        # Get actual costs
        costs = self.cost_calculator.get_costs_by_service(
            start_date=period_start,
            end_date=min(today, period_end),
        )
        actual_amount = sum(costs.values())
        
        # Calculate metrics
        variance = budget_amount - actual_amount
        variance_pct = ((budget_amount - actual_amount) / budget_amount * 100) if budget_amount > 0 else 0
        consumption_pct = (actual_amount / budget_amount * 100) if budget_amount > 0 else 100
        
        # Calculate forecast
        if days_elapsed > 0:
            daily_burn_rate = actual_amount / days_elapsed
            projected_total = daily_burn_rate * days_in_period
            projected_variance = budget_amount - projected_total
        else:
            daily_burn_rate = 0
            projected_total = 0
            projected_variance = budget_amount
        
        status = self.calculate_budget_status(budget_amount, actual_amount, warning_threshold)
        
        return {
            "budget_amount": budget_amount,
            "actual_amount": round(actual_amount, 2),
            "variance": round(variance, 2),
            "variance_pct": round(variance_pct, 2),
            "consumption_pct": round(consumption_pct, 2),
            "status": status.value,
            "period_type": period_type,
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "days_elapsed": days_elapsed,
            "days_remaining": days_in_period - days_elapsed,
            "daily_burn_rate": round(daily_burn_rate, 2),
            "projected_total": round(projected_total, 2),
            "projected_variance": round(projected_variance, 2),
            "projected_status": self.calculate_budget_status(
                budget_amount, projected_total, warning_threshold
            ).value,
            "breakdown_by_service": {k: round(v, 2) for k, v in costs.items()},
        }
    
    def get_budget_recommendations(
        self,
        validation_result: Dict[str, Any],
    ) -> List[str]:
        """Generate budget recommendations based on validation.
        
        Args:
            validation_result: Result from validate_budget().
            
        Returns:
            List of recommendation strings.
        """
        recommendations = []
        status = validation_result.get("status")
        projected_status = validation_result.get("projected_status")
        consumption_pct = validation_result.get("consumption_pct", 0)
        daily_burn_rate = validation_result.get("daily_burn_rate", 0)
        days_remaining = validation_result.get("days_remaining", 0)
        
        if status == BudgetStatus.EXCEEDED.value:
            recommendations.append(
                "🚨 Budget exceeded! Review high-cost resources immediately."
            )
            recommendations.append(
                "Consider rightsizing or terminating unused resources."
            )
        elif status == BudgetStatus.WARNING.value:
            recommendations.append(
                f"⚠️ Budget consumption at {consumption_pct:.1f}%. Monitor closely."
            )
            if projected_status == BudgetStatus.EXCEEDED.value:
                recommendations.append(
                    "At current burn rate, you will exceed budget. Take action now."
                )
        else:
            if projected_status == BudgetStatus.WARNING.value:
                recommendations.append(
                    "Budget is healthy but projected to reach warning level."
                )
            elif projected_status == BudgetStatus.EXCEEDED.value:
                recommendations.append(
                    "Budget is healthy but projected to exceed. Monitor burn rate."
                )
        
        # Service-specific recommendations
        breakdown = validation_result.get("breakdown_by_service", {})
        if breakdown:
            sorted_services = sorted(breakdown.items(), key=lambda x: x[1], reverse=True)
            top_service, top_cost = sorted_services[0] if sorted_services else (None, 0)
            
            if top_service and top_cost > validation_result.get("actual_amount", 0) * 0.5:
                recommendations.append(
                    f"📊 {top_service} accounts for over 50% of costs. Review for optimization."
                )
        
        return recommendations


# Singleton instance
_budget_validator: Optional[BudgetValidatorService] = None


def get_budget_validator() -> BudgetValidatorService:
    """Get or create budget validator service instance."""
    global _budget_validator
    if _budget_validator is None:
        _budget_validator = BudgetValidatorService()
    return _budget_validator

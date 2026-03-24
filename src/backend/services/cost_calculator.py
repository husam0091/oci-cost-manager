"""Cost calculation service using OCI Usage API."""

import time
from datetime import UTC, datetime, timedelta
from typing import Optional, List, Dict, Any
from decimal import Decimal

import oci

from .oci_client import get_oci_client

# Simple in-memory cache
_cache = {}
_cache_ttl = 300  # 5 minutes


def get_cached(key: str):
    """Get cached value if not expired."""
    if key in _cache:
        value, timestamp = _cache[key]
        if time.time() - timestamp < _cache_ttl:
            return value
    return None


def set_cached(key: str, value: Any):
    """Set cached value with timestamp."""
    _cache[key] = (value, time.time())


class CostCalculatorService:
    """Service for calculating and aggregating OCI costs."""
    
    def __init__(self):
        """Initialize cost calculator service."""
        self.oci_client = get_oci_client()
    
    def get_usage_summary(
        self,
        start_date: datetime,
        end_date: datetime,
        granularity: str = "MONTHLY",
        group_by: Optional[List[str]] = None,
        compartment_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get usage summary from OCI Usage API.
        
        Args:
            start_date: Start of the reporting period.
            end_date: End of the reporting period.
            granularity: DAILY or MONTHLY.
            group_by: List of dimensions to group by (e.g., ["service", "skuName"]).
            compartment_id: Optional compartment filter.
            
        Returns:
            List of usage summary items.
        """
        usage_client = self.oci_client.usage_client
        tenancy_id = self.oci_client.tenancy_id
        
        # OCI Usage API requires dates with zero time precision
        start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Build request
        request_details = oci.usage_api.models.RequestSummarizedUsagesDetails(
            tenant_id=tenancy_id,
            time_usage_started=start_date,
            time_usage_ended=end_date,
            granularity=granularity,
            query_type="COST",
            group_by=group_by or ["service", "skuName"],
            compartment_depth=6,
        )
        
        if compartment_id:
            request_details.filter = oci.usage_api.models.Filter(
                dimensions=[
                    oci.usage_api.models.Dimension(
                        key="compartmentId",
                        value=compartment_id
                    )
                ]
            )
        
        # Fetch usage data
        response = None
        last_error = None
        for attempt in range(3):
            try:
                response = usage_client.request_summarized_usages(request_details)
                break
            except oci.exceptions.ServiceError as exc:
                last_error = exc
                is_429 = getattr(exc, "status", None) == 429
                if not is_429 or attempt == 2:
                    raise
                time.sleep(1.5 * (attempt + 1))
        if response is None and last_error:
            raise last_error
        
        items = []
        for item in response.data.items:
            # Get cost amount - try different attribute names
            cost = 0
            if hasattr(item, 'computed_amount') and item.computed_amount:
                cost = float(item.computed_amount)
            elif hasattr(item, 'cost') and item.cost:
                cost = float(item.cost)
            
            items.append({
                "service": getattr(item, "service", None),
                "sku_name": getattr(item, "sku_name", None),
                "sku_part_number": getattr(item, "sku_part_number", None),
                "quantity": float(getattr(item, "quantity", 0) or 0),
                "unit": getattr(item, "unit", None),
                "computed_amount": cost,
                "currency": getattr(item, "currency", "USD"),
                "time_usage_started": item.time_usage_started.isoformat() if getattr(item, "time_usage_started", None) else None,
                "time_usage_ended": item.time_usage_ended.isoformat() if getattr(item, "time_usage_ended", None) else None,
                "compartment_id": getattr(item, "compartment_id", None),
                "compartment_name": getattr(item, "compartment_name", None),
                "resource_id": getattr(item, "resource_id", None),
            })
        
        return items
    
    def get_costs_by_service(
        self,
        start_date: datetime,
        end_date: datetime,
        services: Optional[List[str]] = None,
    ) -> Dict[str, float]:
        """Get costs grouped by service.
        
        Args:
            start_date: Start of the reporting period.
            end_date: End of the reporting period.
            services: Optional list of services to filter.
            
        Returns:
            Dictionary mapping service names to costs.
        """
        # Check cache first
        cache_key = f"costs_by_service_{start_date.date()}_{end_date.date()}"
        cached = get_cached(cache_key)
        if cached is not None:
            return cached
        
        items = self.get_usage_summary(
            start_date=start_date,
            end_date=end_date,
            group_by=["service"],
        )
        
        costs = {}
        for item in items:
            service = item.get("service", "Unknown")
            if services and service not in services:
                continue
            costs[service] = costs.get(service, 0) + item.get("computed_amount", 0)
        
        # Cache the result
        set_cached(cache_key, costs)
        
        return costs
    
    def get_costs_by_resource(
        self,
        start_date: datetime,
        end_date: datetime,
        compartment_id: Optional[str] = None,
        include_skus: bool = True,
    ) -> List[Dict[str, Any]]:
        """Get costs grouped by resource.
        
        Args:
            start_date: Start of the reporting period.
            end_date: End of the reporting period.
            compartment_id: Optional compartment filter.
            
        Returns:
            List of resource cost items.
        """
        group_by = ["resourceId", "skuName"] if include_skus else ["resourceId"]
        items = self.get_usage_summary(
            start_date=start_date,
            end_date=end_date,
            group_by=group_by,
            compartment_id=compartment_id,
        )
        
        # Aggregate by resource
        resource_costs = {}
        for item in items:
            resource_id = item.get("resource_id", "Unknown")
            if resource_id not in resource_costs:
                resource_costs[resource_id] = {
                    "resource_id": resource_id,
                    "compartment_id": item.get("compartment_id"),
                    "compartment_name": item.get("compartment_name"),
                    "total_cost": 0,
                    "skus": [],
                }
            
            resource_costs[resource_id]["total_cost"] += item.get("computed_amount", 0)
            if include_skus:
                resource_costs[resource_id]["skus"].append({
                    "sku_name": item.get("sku_name"),
                    "sku_part_number": item.get("sku_part_number"),
                    "quantity": item.get("quantity"),
                    "unit": item.get("unit"),
                    "cost": item.get("computed_amount"),
                })
        
        return list(resource_costs.values())
    
    def get_database_costs(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> Dict[str, Any]:
        """Get costs for all database services.
        
        Args:
            start_date: Start of the reporting period.
            end_date: End of the reporting period.
            
        Returns:
            Dictionary with database cost breakdown.
        """
        # Database-related services
        db_services = [
            "ORACLE_DATABASE",
            "MYSQL",
            "DATABASE",
            "AUTONOMOUS_DATABASE",
        ]
        
        items = self.get_usage_summary(
            start_date=start_date,
            end_date=end_date,
            group_by=["service", "skuName", "skuPartNumber"],
        )
        
        result = {
            "oracle_db": {"total": 0, "skus": []},
            "mysql": {"total": 0, "skus": []},
            "sql_server": {"total": 0, "skus": []},
            "autonomous_db": {"total": 0, "skus": []},
            "total": 0,
        }
        
        for item in items:
            service = item.get("service", "").upper()
            sku_name = item.get("sku_name", "").lower()
            cost = item.get("computed_amount", 0)
            
            sku_info = {
                "sku_name": item.get("sku_name"),
                "sku_part_number": item.get("sku_part_number"),
                "quantity": item.get("quantity"),
                "unit": item.get("unit"),
                "cost": cost,
            }
            
            # Categorize by service type
            if "ORACLE" in service or "DATABASE" in service:
                if "AUTONOMOUS" in service:
                    result["autonomous_db"]["total"] += cost
                    result["autonomous_db"]["skus"].append(sku_info)
                else:
                    result["oracle_db"]["total"] += cost
                    result["oracle_db"]["skus"].append(sku_info)
            elif "MYSQL" in service:
                result["mysql"]["total"] += cost
                result["mysql"]["skus"].append(sku_info)
            elif "sql server" in sku_name or "microsoft" in sku_name:
                result["sql_server"]["total"] += cost
                result["sql_server"]["skus"].append(sku_info)
        
        result["total"] = (
            result["oracle_db"]["total"] +
            result["mysql"]["total"] +
            result["sql_server"]["total"] +
            result["autonomous_db"]["total"]
        )
        
        return result
    
    def get_daily_costs(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> List[Dict[str, Any]]:
        """Get costs broken down by day and service (mirrors OCI Cost Analysis daily view).

        Returns:
            List of {date, total, by_service} dicts ordered by date.
        """
        cache_key = f"daily_costs_{start_date.date()}_{end_date.date()}"
        cached = get_cached(cache_key)
        if cached is not None:
            return cached

        items = self.get_usage_summary(
            start_date=start_date,
            end_date=end_date,
            granularity="DAILY",
            group_by=["service"],
        )

        by_date: Dict[str, Dict] = {}
        for item in items:
            date_key = (item.get("time_usage_started") or "")[:10]
            if not date_key:
                continue
            service = item.get("service") or "Other"
            cost = float(item.get("computed_amount") or 0)
            if date_key not in by_date:
                by_date[date_key] = {"date": date_key, "total": 0.0, "by_service": {}}
            by_date[date_key]["total"] = round(by_date[date_key]["total"] + cost, 4)
            by_date[date_key]["by_service"][service] = round(
                by_date[date_key]["by_service"].get(service, 0.0) + cost, 4
            )

        result = [v for _, v in sorted(by_date.items())]
        set_cached(cache_key, result)
        return result

    def get_cost_trends(
        self,
        months: int = 6,
    ) -> List[Dict[str, Any]]:
        """Get monthly cost trends.
        
        Args:
            months: Number of months to include.
            
        Returns:
            List of monthly cost data points.
        """
        trends = []
        today = datetime.now(UTC)
        
        for i in range(months - 1, -1, -1):
            # Calculate month boundaries
            month_start = (today.replace(day=1) - timedelta(days=i * 30)).replace(day=1)
            if i == 0:
                month_end = today
            else:
                next_month = month_start.replace(day=28) + timedelta(days=4)
                month_end = next_month.replace(day=1)
            
            costs = self.get_costs_by_service(
                start_date=month_start,
                end_date=month_end,
            )
            
            trends.append({
                "month": month_start.strftime("%Y-%m"),
                "month_name": month_start.strftime("%B %Y"),
                "total_cost": sum(costs.values()),
                "by_service": costs,
            })
        
        return trends


# Singleton instance
_cost_calculator: Optional[CostCalculatorService] = None


def get_cost_calculator() -> CostCalculatorService:
    """Get or create cost calculator service instance."""
    global _cost_calculator
    if _cost_calculator is None:
        _cost_calculator = CostCalculatorService()
    return _cost_calculator

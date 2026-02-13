"""Price updater service for fetching OCI prices from official API."""

import httpx
from datetime import UTC, datetime
from typing import Optional, Dict, Any, List

from core.config import get_settings


class PriceUpdaterService:
    """Service for fetching and managing OCI prices."""
    
    def __init__(self):
        """Initialize price updater service."""
        settings = get_settings()
        self.price_api_url = settings.oci_price_api_url
        self._cache: Dict[str, Any] = {}
        self._cache_timestamp: Optional[datetime] = None
        self._cache_ttl = settings.cache_ttl_prices
    
    async def fetch_prices(
        self,
        service_name: Optional[str] = None,
        region: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch prices from OCI Price List API.
        
        Args:
            service_name: Optional service name filter (e.g., "Database").
            region: Optional region filter.
            
        Returns:
            List of price items.
        """
        params = {}
        if service_name:
            params["serviceName"] = service_name
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(self.price_api_url, params=params)
            response.raise_for_status()
            data = response.json()
        
        items = data.get("items", [])
        
        # Filter by region if specified
        if region:
            items = [
                item for item in items
                if item.get("region", "").lower() == region.lower()
            ]
        
        return items
    
    def fetch_prices_sync(
        self,
        service_name: Optional[str] = None,
        region: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Synchronous version of fetch_prices.
        
        Args:
            service_name: Optional service name filter.
            region: Optional region filter.
            
        Returns:
            List of price items.
        """
        params = {}
        if service_name:
            params["serviceName"] = service_name
        
        with httpx.Client(timeout=30.0) as client:
            response = client.get(self.price_api_url, params=params)
            response.raise_for_status()
            data = response.json()
        
        items = data.get("items", [])
        
        if region:
            items = [
                item for item in items
                if item.get("region", "").lower() == region.lower()
            ]
        
        return items
    
    def get_database_prices(
        self,
        region: Optional[str] = None,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Get prices for database services.
        
        Args:
            region: Optional region filter.
            
        Returns:
            Dictionary with prices grouped by database type.
        """
        # Check cache
        cache_key = f"db_prices_{region or 'all'}"
        if self._is_cache_valid(cache_key):
            return self._cache[cache_key]
        
        result = {
            "oracle_db": [],
            "mysql": [],
            "autonomous_db": [],
            "sql_server": [],
        }
        
        # Fetch database prices
        db_prices = self.fetch_prices_sync(service_name="Database", region=region)
        mysql_prices = self.fetch_prices_sync(service_name="MySQL", region=region)
        compute_prices = self.fetch_prices_sync(service_name="Compute", region=region)
        
        # Categorize prices
        for price in db_prices:
            product_name = price.get("productName", "").lower()
            if "autonomous" in product_name:
                result["autonomous_db"].append(self._format_price(price))
            else:
                result["oracle_db"].append(self._format_price(price))
        
        for price in mysql_prices:
            result["mysql"].append(self._format_price(price))
        
        # SQL Server prices (from compute with Windows/SQL images)
        for price in compute_prices:
            product_name = price.get("productName", "").lower()
            if "sql server" in product_name or "microsoft" in product_name:
                result["sql_server"].append(self._format_price(price))
        
        # Update cache
        self._cache[cache_key] = result
        self._cache_timestamp = datetime.now(UTC)
        
        return result
    
    def get_price_by_sku(
        self,
        sku_part_number: str,
        region: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Get price for a specific SKU.
        
        Args:
            sku_part_number: SKU part number.
            region: Optional region filter.
            
        Returns:
            Price info or None if not found.
        """
        # Try to find in cache first
        all_prices = self.fetch_prices_sync(region=region)
        
        for price in all_prices:
            if price.get("partNumber") == sku_part_number:
                return self._format_price(price)
        
        return None
    
    def compare_prices(
        self,
        old_prices: List[Dict[str, Any]],
        new_prices: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Compare old and new prices to find changes.
        
        Args:
            old_prices: Previous price list.
            new_prices: Current price list.
            
        Returns:
            List of price changes.
        """
        changes = []
        
        # Create lookup for old prices
        old_lookup = {p.get("sku_part_number"): p for p in old_prices}
        
        for new_price in new_prices:
            sku = new_price.get("sku_part_number")
            old_price = old_lookup.get(sku)
            
            if old_price is None:
                changes.append({
                    "type": "new",
                    "sku_part_number": sku,
                    "product_name": new_price.get("product_name"),
                    "new_price": new_price.get("unit_price"),
                })
            elif old_price.get("unit_price") != new_price.get("unit_price"):
                changes.append({
                    "type": "changed",
                    "sku_part_number": sku,
                    "product_name": new_price.get("product_name"),
                    "old_price": old_price.get("unit_price"),
                    "new_price": new_price.get("unit_price"),
                    "change_pct": self._calc_change_pct(
                        old_price.get("unit_price", 0),
                        new_price.get("unit_price", 0),
                    ),
                })
        
        # Check for removed prices
        new_lookup = {p.get("sku_part_number"): p for p in new_prices}
        for old_price in old_prices:
            sku = old_price.get("sku_part_number")
            if sku not in new_lookup:
                changes.append({
                    "type": "removed",
                    "sku_part_number": sku,
                    "product_name": old_price.get("product_name"),
                    "old_price": old_price.get("unit_price"),
                })
        
        return changes
    
    def _format_price(self, raw_price: Dict[str, Any]) -> Dict[str, Any]:
        """Format raw price data into standard structure.
        
        Args:
            raw_price: Raw price data from API.
            
        Returns:
            Formatted price dictionary.
        """
        return {
            "sku_part_number": raw_price.get("partNumber"),
            "service_name": raw_price.get("serviceName"),
            "product_name": raw_price.get("productName"),
            "unit_price": raw_price.get("unitPrice"),
            "currency": raw_price.get("currencyCode", "USD"),
            "unit": raw_price.get("unit"),
            "region": raw_price.get("region"),
            "description": raw_price.get("description"),
        }
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cache is valid.
        
        Args:
            cache_key: Cache key to check.
            
        Returns:
            True if cache is valid, False otherwise.
        """
        if cache_key not in self._cache:
            return False
        
        if self._cache_timestamp is None:
            return False
        
        elapsed = (datetime.now(UTC) - self._cache_timestamp).total_seconds()
        return elapsed < self._cache_ttl
    
    def _calc_change_pct(self, old_value: float, new_value: float) -> float:
        """Calculate percentage change.
        
        Args:
            old_value: Previous value.
            new_value: New value.
            
        Returns:
            Percentage change.
        """
        if old_value == 0:
            return 100.0 if new_value > 0 else 0.0
        return round(((new_value - old_value) / old_value) * 100, 2)
    
    def clear_cache(self) -> None:
        """Clear the price cache."""
        self._cache.clear()
        self._cache_timestamp = None


# Singleton instance
_price_updater: Optional[PriceUpdaterService] = None


def get_price_updater() -> PriceUpdaterService:
    """Get or create price updater service instance."""
    global _price_updater
    if _price_updater is None:
        _price_updater = PriceUpdaterService()
    return _price_updater

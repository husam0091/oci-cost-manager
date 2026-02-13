"""Price API endpoints."""

from typing import Optional
from fastapi import APIRouter, HTTPException, Query

from services import get_price_updater, get_oci_client

router = APIRouter()


@router.get("")
async def list_prices(
    service: Optional[str] = Query(None, description="Filter by service: Database, MySQL, Compute"),
    region: Optional[str] = Query(None, description="Filter by region"),
):
    """List all prices from OCI Price List."""
    try:
        updater = get_price_updater()
        
        # Get region from OCI client if not specified
        if not region:
            try:
                oci_client = get_oci_client()
                region = oci_client.region
            except Exception:
                pass
        
        prices = updater.fetch_prices_sync(service_name=service, region=region)
        
        # Format prices
        formatted = [updater._format_price(p) for p in prices]
        
        return {
            "success": True,
            "data": formatted,
            "meta": {
                "total": len(formatted),
                "region": region,
                "service_filter": service,
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/databases")
async def get_database_prices(
    region: Optional[str] = Query(None, description="Filter by region"),
):
    """Get prices for all database services."""
    try:
        updater = get_price_updater()
        
        # Get region from OCI client if not specified
        if not region:
            try:
                oci_client = get_oci_client()
                region = oci_client.region
            except Exception:
                pass
        
        db_prices = updater.get_database_prices(region)
        
        return {
            "success": True,
            "data": db_prices,
            "meta": {"region": region},
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sku/{sku_part_number}")
async def get_price_by_sku(
    sku_part_number: str,
    region: Optional[str] = Query(None, description="Filter by region"),
):
    """Get price for a specific SKU."""
    try:
        updater = get_price_updater()
        price = updater.get_price_by_sku(sku_part_number, region)
        
        if price is None:
            raise HTTPException(status_code=404, detail=f"SKU {sku_part_number} not found")
        
        return {
            "success": True,
            "data": price,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/refresh")
async def refresh_prices():
    """Refresh prices from OCI Price List API."""
    try:
        updater = get_price_updater()
        updater.clear_cache()
        
        # Fetch fresh prices
        prices = updater.fetch_prices_sync()
        
        return {
            "success": True,
            "message": f"Refreshed {len(prices)} prices",
            "meta": {"total": len(prices)},
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/services")
async def list_services():
    """List available OCI services with pricing."""
    try:
        updater = get_price_updater()
        prices = updater.fetch_prices_sync()
        
        # Get unique services
        services = set()
        for price in prices:
            service = price.get("serviceName")
            if service:
                services.add(service)
        
        return {
            "success": True,
            "data": sorted(list(services)),
            "meta": {"total": len(services)},
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/regions")
async def list_regions():
    """List available regions with pricing."""
    try:
        updater = get_price_updater()
        prices = updater.fetch_prices_sync()
        
        # Get unique regions
        regions = set()
        for price in prices:
            region = price.get("region")
            if region:
                regions.add(region)
        
        return {
            "success": True,
            "data": sorted(list(regions)),
            "meta": {"total": len(regions)},
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

"""Cache management endpoints."""

import uuid
from fastapi import APIRouter, Request
from core.cache import clear_cache, get_cache_info
from core.redis_cache import cache_delete_prefix
from services.event_logger import audit_event, log_event

router = APIRouter()


@router.get("")
async def get_cache_status():
    """Get cache status and entries."""
    return {
        "success": True,
        "data": get_cache_info(),
    }


@router.delete("")
async def clear_all_cache():
    """Clear all cached data."""
    clear_cache()
    return {
        "success": True,
        "message": "Cache cleared",
    }


@router.delete("/{cache_key}")
async def clear_cache_key(cache_key: str):
    """Clear specific cache key."""
    clear_cache(cache_key)
    return {
        "success": True,
        "message": f"Cache key '{cache_key}' cleared",
    }


@router.post("/bust")
async def bust_cache(request: Request):
    """Bust all phase-3 cost cache keys."""
    correlation_id = request.headers.get("x-correlation-id") or str(uuid.uuid4())
    cache_delete_prefix("cost:")
    cache_delete_prefix("snap:")
    clear_cache()
    actor = request.headers.get("x-user") or "anonymous"
    audit_event(
        actor=actor,
        action="cache_bust",
        target="cache",
        correlation_id=correlation_id,
        meta={"prefixes": ["cost:", "snap:"]},
    )
    log_event(
        level="warn",
        log_type="security",
        source="api",
        message="cache_bust_invoked",
        actor=actor,
        correlation_id=correlation_id,
    )
    return {
        "success": True,
        "message": "Cost cache bust completed",
    }

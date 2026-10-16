"""Cache service for storing API responses."""

import json
import logging
import os
import tempfile
import time
from typing import Optional, Any
from pathlib import Path

# File-based cache (simpler than SQLite for this use case)
CACHE_DIR = Path(__file__).parent.parent / "cache"
CACHE_DIR.mkdir(exist_ok=True)

# Cache TTL in seconds (1 hour default)
DEFAULT_TTL = 3600
CACHE_STATS = {"hits": 0, "misses": 0, "sets": 0}


def _get_cache_file(key: str) -> Path:
    """Get cache file path for a key."""
    safe_key = key.replace("/", "_").replace(":", "_")
    return CACHE_DIR / f"{safe_key}.json"


def get_cached(key: str) -> Optional[Any]:
    """Get cached value if not expired.
    
    Args:
        key: Cache key.
        
    Returns:
        Cached value or None if expired/not found.
    """
    cache_file = _get_cache_file(key)
    
    if not cache_file.exists():
        CACHE_STATS["misses"] += 1
        return None
    
    try:
        with open(cache_file, "r") as f:
            data = json.load(f)
        
        # Check if expired
        if time.time() - data.get("timestamp", 0) > data.get("ttl", DEFAULT_TTL):
            CACHE_STATS["misses"] += 1
            return None
        CACHE_STATS["hits"] += 1
        return data.get("value")
    except Exception:
        CACHE_STATS["misses"] += 1
        return None


def set_cached(key: str, value: Any, ttl: int = DEFAULT_TTL):
    """Set cached value with TTL.
    
    Args:
        key: Cache key.
        value: Value to cache.
        ttl: Time to live in seconds.
    """
    cache_file = _get_cache_file(key)
    temporary_path = None
    try:
        # Serialize first: a bad value must not destroy the previous good entry.
        payload = json.dumps({"value": value, "timestamp": time.time(), "ttl": ttl}, allow_nan=False)
        # Readers see either the old or the new complete JSON document, including
        # when multiple API/worker processes update the same key concurrently.
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=CACHE_DIR, suffix=".tmp", delete=False) as handle:
            temporary_path = Path(handle.name)
            handle.write(payload)
        os.replace(temporary_path, cache_file)
        CACHE_STATS["sets"] += 1
    except (OSError, TypeError, ValueError):
        logging.getLogger(__name__).warning("Cache write failed", exc_info=True)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def clear_cache(key: Optional[str] = None):
    """Clear cache.
    
    Args:
        key: Specific key to clear, or None to clear all.
    """
    if key:
        cache_file = _get_cache_file(key)
        cache_file.unlink(missing_ok=True)
    else:
        for cache_file in CACHE_DIR.glob("*.json"):
            cache_file.unlink(missing_ok=True)


def get_cache_info() -> dict:
    """Get cache status info."""
    cache_files = list(CACHE_DIR.glob("*.json"))
    info = {
        "total_entries": len(cache_files),
        "entries": [],
    }
    
    for cache_file in cache_files:
        try:
            with open(cache_file, "r") as f:
                data = json.load(f)
            
            age = time.time() - data.get("timestamp", 0)
            ttl = data.get("ttl", DEFAULT_TTL)
            
            info["entries"].append({
                "key": cache_file.stem,
                "age_seconds": int(age),
                "ttl_seconds": ttl,
                "expired": age > ttl,
            })
        except Exception:
            pass
    
    return info


def get_cache_metrics() -> dict:
    hits = CACHE_STATS.get("hits", 0)
    misses = CACHE_STATS.get("misses", 0)
    total = hits + misses
    return {
        "hits": hits,
        "misses": misses,
        "sets": CACHE_STATS.get("sets", 0),
        "hit_ratio": round((hits / total), 4) if total else 0.0,
    }

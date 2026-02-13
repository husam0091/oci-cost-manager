"""Cache service for storing API responses."""

import json
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
    
    try:
        with open(cache_file, "w") as f:
            json.dump({
                "value": value,
                "timestamp": time.time(),
                "ttl": ttl,
            }, f)
        CACHE_STATS["sets"] += 1
    except Exception as e:
        print(f"Cache write error: {e}")


def clear_cache(key: Optional[str] = None):
    """Clear cache.
    
    Args:
        key: Specific key to clear, or None to clear all.
    """
    if key:
        cache_file = _get_cache_file(key)
        if cache_file.exists():
            cache_file.unlink()
    else:
        for cache_file in CACHE_DIR.glob("*.json"):
            cache_file.unlink()


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

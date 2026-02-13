"""Redis-backed cache helpers with graceful in-memory/file fallback."""

from __future__ import annotations

import json
import os
from typing import Any, Optional

from core.cache import get_cached as file_get_cached
from core.cache import set_cached as file_set_cached
from core.cache import clear_cache as file_clear_cache

try:
    import redis
except Exception:  # pragma: no cover - fallback path
    redis = None


_client = None


def _get_client():
    global _client
    if _client is not None:
        return _client
    if redis is None:
        return None
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        return None
    try:
        _client = redis.Redis.from_url(redis_url, decode_responses=True)
        _client.ping()
        return _client
    except Exception:
        _client = None
        return None


def cache_get(key: str) -> Optional[Any]:
    client = _get_client()
    if client is None:
        return file_get_cached(key)
    try:
        raw = client.get(key)
        if raw is None:
            return None
        return json.loads(raw)
    except Exception:
        return file_get_cached(key)


def cache_set(key: str, value: Any, ttl_seconds: int) -> None:
    client = _get_client()
    if client is None:
        file_set_cached(key, value, ttl_seconds)
        return
    try:
        client.setex(key, ttl_seconds, json.dumps(value))
    except Exception:
        file_set_cached(key, value, ttl_seconds)


def cache_delete_prefix(prefix: str) -> None:
    client = _get_client()
    if client is None:
        file_clear_cache()
        return
    try:
        keys = list(client.scan_iter(f"{prefix}*"))
        if keys:
            client.delete(*keys)
    except Exception:
        file_clear_cache()


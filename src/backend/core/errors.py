"""Shared API error helpers."""

from __future__ import annotations

from fastapi import HTTPException


def raise_production_block(field: str, correlation_id: str | None = None):
    payload = {
        "success": False,
        "error": {
            "code": "FIELD_BLOCKED_IN_PRODUCTION",
            "field": field,
            "message": "Filesystem key mode is disabled in production",
        },
    }
    if correlation_id:
        payload["error"]["correlation_id"] = correlation_id
    raise HTTPException(status_code=400, detail=payload)


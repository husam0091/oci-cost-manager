"""Secret resolution helpers (env-first with optional vault-style indirection)."""

from __future__ import annotations

import json
from typing import Optional


def _vault_store() -> dict[str, str]:
    raw = (__import__("os").environ.get("OCI_VAULT_SECRETS_JSON") or "").strip()
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except Exception:
        return {}
    if not isinstance(data, dict):
        return {}
    return {str(k): str(v) for k, v in data.items()}


def resolve_secret(value: Optional[str], *, env_var: Optional[str] = None) -> Optional[str]:
    """Resolve a secret value.

    Resolution order:
    1) Explicit environment variable (if provided)
    2) Literal value unless it uses vault://KEY syntax
    3) vault://KEY -> env: OCI_VAULT_SECRET_KEY or OCI_VAULT_SECRETS_JSON map entry
    """
    env = __import__("os").environ
    if env_var:
        direct = (env.get(env_var) or "").strip()
        if direct:
            return direct

    raw = (value or "").strip()
    if not raw:
        return None
    if not raw.lower().startswith("vault://"):
        return raw

    key = raw.split("://", 1)[1].strip()
    if not key:
        return None
    env_key = f"OCI_VAULT_SECRET_{key.upper()}"
    if env.get(env_key):
        return env.get(env_key)
    return _vault_store().get(key)


def mask_secret(value: Optional[str]) -> Optional[str]:
    """Mask a secret for logs/UI diagnostics."""
    if value is None:
        return None
    text = str(value)
    if len(text) <= 6:
        return "***"
    return f"{text[:2]}***{text[-2:]}"


"""Unit tests for core/secrets.py — env-first secret resolution and masking."""

from __future__ import annotations

import json

import pytest

from core.secrets import mask_secret, resolve_secret


# ---------------------------------------------------------------------------
# mask_secret
# ---------------------------------------------------------------------------

def test_mask_secret_short_input_fully_masked():
    assert mask_secret("abc") == "***"
    assert mask_secret("abcdef") == "***"


def test_mask_secret_longer_keeps_two_chars_on_each_side():
    assert mask_secret("hunter2-secret") == "hu***et"


def test_mask_secret_none_input_returns_none():
    assert mask_secret(None) is None


def test_mask_secret_handles_non_string_input():
    """The function coerces input to string."""
    assert mask_secret(12345) == "***"


# ---------------------------------------------------------------------------
# resolve_secret — env_var takes priority over literal
# ---------------------------------------------------------------------------

def test_resolve_secret_env_var_wins(monkeypatch):
    monkeypatch.setenv("MY_SECRET", "from-env")
    assert resolve_secret("ignored", env_var="MY_SECRET") == "from-env"


def test_resolve_secret_env_var_missing_falls_back_to_literal(monkeypatch):
    monkeypatch.delenv("MISSING_ENV", raising=False)
    assert resolve_secret("plain-value", env_var="MISSING_ENV") == "plain-value"


def test_resolve_secret_returns_literal_when_no_env_var():
    assert resolve_secret("plain") == "plain"


def test_resolve_secret_strips_whitespace():
    assert resolve_secret("  padded  ") == "padded"


def test_resolve_secret_empty_input_returns_none():
    assert resolve_secret("") is None
    assert resolve_secret(None) is None
    assert resolve_secret("   ") is None


# ---------------------------------------------------------------------------
# vault://KEY indirection
# ---------------------------------------------------------------------------

def test_resolve_secret_vault_uses_dedicated_env_var(monkeypatch):
    monkeypatch.setenv("OCI_VAULT_SECRET_DB_PASSWORD", "vault-value")
    assert resolve_secret("vault://db_password") == "vault-value"


def test_resolve_secret_vault_falls_back_to_json_map(monkeypatch):
    monkeypatch.delenv("OCI_VAULT_SECRET_API_KEY", raising=False)
    monkeypatch.setenv(
        "OCI_VAULT_SECRETS_JSON",
        json.dumps({"api_key": "from-json", "other": "x"}),
    )
    assert resolve_secret("vault://api_key") == "from-json"


def test_resolve_secret_vault_unknown_key_returns_none(monkeypatch):
    monkeypatch.delenv("OCI_VAULT_SECRET_NOT_THERE", raising=False)
    monkeypatch.setenv("OCI_VAULT_SECRETS_JSON", "{}")
    assert resolve_secret("vault://not_there") is None


def test_resolve_secret_vault_with_empty_key_returns_none():
    assert resolve_secret("vault://") is None


def test_resolve_secret_vault_invalid_json_treated_as_empty(monkeypatch):
    monkeypatch.delenv("OCI_VAULT_SECRET_FOO", raising=False)
    monkeypatch.setenv("OCI_VAULT_SECRETS_JSON", "not-a-json")
    assert resolve_secret("vault://foo") is None


def test_resolve_secret_vault_non_dict_json_ignored(monkeypatch):
    monkeypatch.delenv("OCI_VAULT_SECRET_FOO", raising=False)
    monkeypatch.setenv("OCI_VAULT_SECRETS_JSON", "[1, 2, 3]")
    assert resolve_secret("vault://foo") is None


def test_resolve_secret_vault_case_insensitive_prefix():
    """vault://KEY should be recognized regardless of case."""
    import os
    # Manually set then assert no exception path triggered
    os.environ["OCI_VAULT_SECRET_KEYNAME"] = "ok"
    try:
        assert resolve_secret("Vault://keyname") == "ok"
    finally:
        os.environ.pop("OCI_VAULT_SECRET_KEYNAME", None)

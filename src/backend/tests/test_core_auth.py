"""Unit tests for core/auth.py (password hashing + JWT issuance/verification)."""

from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta

from jose import jwt

from core import auth


def test_hash_password_is_not_plaintext():
    h = auth.hash_password("hunter2")
    assert h and h != "hunter2"
    # bcrypt prefix
    assert h.startswith("$2")


def test_verify_password_accepts_correct_password():
    h = auth.hash_password("hunter2")
    assert auth.verify_password("hunter2", h) is True


def test_verify_password_rejects_wrong_password():
    h = auth.hash_password("hunter2")
    assert auth.verify_password("wrong", h) is False


def test_hash_password_uses_unique_salt():
    """bcrypt salts each hash — two hashes of the same input must differ."""
    a = auth.hash_password("same")
    b = auth.hash_password("same")
    assert a != b


def test_create_and_decode_access_token_roundtrip():
    token = auth.create_access_token("alice")
    payload = auth.decode_token(token)
    assert payload is not None
    assert payload["sub"] == "alice"
    assert "exp" in payload
    assert "iat" in payload


def test_decode_token_returns_none_for_garbage():
    assert auth.decode_token("not-a-jwt") is None


def test_decode_token_returns_none_for_tampered_signature():
    token = auth.create_access_token("alice")
    head, body, sig = token.split(".")
    tampered = f"{head}.{body}.{sig[:-2]}XX"
    assert auth.decode_token(tampered) is None


def test_decode_token_returns_none_when_expired(monkeypatch):
    """An already-expired token must not validate."""
    expired = jwt.encode(
        {
            "sub": "bob",
            "exp": datetime.now(UTC) - timedelta(minutes=1),
            "iat": datetime.now(UTC) - timedelta(minutes=2),
        },
        auth.get_secret_key(),
        algorithm="HS256",
    )
    assert auth.decode_token(expired) is None


def test_decode_token_returns_none_when_signed_with_different_secret():
    bad_token = jwt.encode(
        {"sub": "alice", "exp": datetime.now(UTC) + timedelta(minutes=5)},
        "different-secret",
        algorithm="HS256",
    )
    assert auth.decode_token(bad_token) is None


def test_create_access_token_respects_custom_expiry():
    token = auth.create_access_token("alice", expires_minutes=5)
    payload = auth.decode_token(token)
    assert payload is not None
    iat = payload["iat"]
    exp = payload["exp"]
    # 5 minutes ± small skew for execution time
    assert 295 <= (exp - iat) <= 305

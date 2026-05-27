"""Unit tests for core/crypto.py (AES-GCM secret encryption)."""

from __future__ import annotations

import base64

import pytest

from core import crypto
from core.config import get_settings


@pytest.fixture(autouse=True)
def _provide_master_key(monkeypatch):
    """Force a deterministic master key for these tests."""
    raw = b"A" * 32
    encoded = base64.b64encode(raw).decode("utf-8")
    settings = get_settings()
    monkeypatch.setattr(settings, "app_master_key", encoded, raising=False)
    yield


def test_encrypt_decrypt_roundtrip():
    payload = crypto.encrypt_secret("oracle-cloud-secret-123")
    assert payload.ciphertext
    assert payload.nonce
    assert payload.salt
    assert payload.key_version == "v1"

    plaintext = crypto.decrypt_secret(payload.ciphertext, payload.nonce, payload.salt)
    assert plaintext == "oracle-cloud-secret-123"


def test_encrypt_produces_unique_ciphertext_for_same_plaintext():
    """Each encrypt uses a fresh nonce+salt, so ciphertexts must differ."""
    a = crypto.encrypt_secret("same-secret")
    b = crypto.encrypt_secret("same-secret")
    assert a.ciphertext != b.ciphertext
    assert a.nonce != b.nonce
    assert a.salt != b.salt


def test_decrypt_with_wrong_salt_fails():
    payload = crypto.encrypt_secret("secret")
    bad_salt = base64.b64encode(b"B" * 16).decode("utf-8")
    with pytest.raises(Exception):
        crypto.decrypt_secret(payload.ciphertext, payload.nonce, bad_salt)


def test_decrypt_with_wrong_nonce_fails():
    payload = crypto.encrypt_secret("secret")
    bad_nonce = base64.b64encode(b"B" * 12).decode("utf-8")
    with pytest.raises(Exception):
        crypto.decrypt_secret(payload.ciphertext, bad_nonce, payload.salt)


def test_decrypt_tampered_ciphertext_fails():
    payload = crypto.encrypt_secret("secret")
    raw = base64.b64decode(payload.ciphertext)
    tampered = bytearray(raw)
    tampered[0] ^= 0x01
    bad_ct = base64.b64encode(bytes(tampered)).decode("utf-8")
    with pytest.raises(Exception):
        crypto.decrypt_secret(bad_ct, payload.nonce, payload.salt)


def test_encrypt_requires_non_none_plaintext():
    with pytest.raises(ValueError):
        crypto.encrypt_secret(None)  # type: ignore[arg-type]


def test_encrypt_empty_string_is_allowed():
    payload = crypto.encrypt_secret("")
    assert crypto.decrypt_secret(payload.ciphertext, payload.nonce, payload.salt) == ""


def test_short_master_key_rejected(monkeypatch):
    """A master key shorter than 32 bytes must be refused."""
    settings = get_settings()
    monkeypatch.setattr(settings, "app_master_key", "short", raising=False)
    monkeypatch.setattr(crypto, "_KEY_FILE", "/nonexistent/master.key")
    with pytest.raises(RuntimeError):
        crypto.encrypt_secret("anything")

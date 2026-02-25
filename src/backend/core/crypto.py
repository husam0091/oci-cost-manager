"""Encryption helpers for secret-at-rest protection."""

from __future__ import annotations

import base64
import os
from dataclasses import dataclass

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes

from core.config import get_settings


@dataclass
class EncryptedPayload:
    ciphertext: str
    nonce: str
    salt: str
    key_version: str = "v1"


def _load_master_key() -> bytes:
    settings = get_settings()
    raw = (settings.app_master_key or "").strip()
    if not raw:
        raise RuntimeError("APP_MASTER_KEY is required for secret encryption")
    try:
        decoded = base64.b64decode(raw, validate=True)
    except Exception:
        decoded = raw.encode("utf-8")
    if len(decoded) < 32:
        raise RuntimeError("APP_MASTER_KEY must be at least 32 bytes")
    return decoded[:32]


def _derive_key(master_key: bytes, salt: bytes) -> bytes:
    hkdf = HKDF(algorithm=hashes.SHA256(), length=32, salt=salt, info=b"oci-cost-manager/secret/v1")
    return hkdf.derive(master_key)


def encrypt_secret(secret_plaintext: str) -> EncryptedPayload:
    if secret_plaintext is None:
        raise ValueError("secret_plaintext is required")
    master_key = _load_master_key()
    salt = os.urandom(16)
    nonce = os.urandom(12)
    data_key = _derive_key(master_key, salt)
    aesgcm = AESGCM(data_key)
    ciphertext = aesgcm.encrypt(nonce, secret_plaintext.encode("utf-8"), None)
    return EncryptedPayload(
        ciphertext=base64.b64encode(ciphertext).decode("utf-8"),
        nonce=base64.b64encode(nonce).decode("utf-8"),
        salt=base64.b64encode(salt).decode("utf-8"),
        key_version="v1",
    )


def decrypt_secret(ciphertext: str, nonce: str, salt: str) -> str:
    master_key = _load_master_key()
    nonce_bytes = base64.b64decode(nonce)
    salt_bytes = base64.b64decode(salt)
    ciphertext_bytes = base64.b64decode(ciphertext)
    data_key = _derive_key(master_key, salt_bytes)
    aesgcm = AESGCM(data_key)
    plaintext = aesgcm.decrypt(nonce_bytes, ciphertext_bytes, None)
    return plaintext.decode("utf-8")


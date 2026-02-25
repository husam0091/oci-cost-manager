"""Secure OCI credential storage/retrieval."""

from __future__ import annotations

from datetime import UTC, datetime
import re
from typing import Any

from sqlalchemy.orm import Session

from core.crypto import decrypt_secret, encrypt_secret
from core.models import EncryptedSecret, OciIntegration

_PEM_BLOCK_PATTERN = re.compile(r"-----BEGIN [A-Z0-9 _-]+-----[\s\S]+-----END [A-Z0-9 _-]+-----", re.MULTILINE)


def validate_pem(pem_text: str) -> None:
    text = (pem_text or "").strip()
    if not text:
        raise ValueError("PEM content is required")
    if not _PEM_BLOCK_PATTERN.search(text):
        raise ValueError("Invalid PEM format")


def upsert_oci_metadata(
    db: Session,
    *,
    user_ocid: str,
    tenancy_ocid: str,
    fingerprint: str,
    region: str,
    actor: str,
) -> OciIntegration:
    row = db.query(OciIntegration).order_by(OciIntegration.id.desc()).first()
    if not row:
        row = OciIntegration(
            user_ocid=user_ocid.strip(),
            tenancy_ocid=tenancy_ocid.strip(),
            fingerprint=fingerprint.strip(),
            region=region.strip(),
            status="degraded",
            created_at=datetime.now(UTC),
            created_by=actor,
            updated_by=actor,
        )
        db.add(row)
    else:
        row.user_ocid = user_ocid.strip()
        row.tenancy_ocid = tenancy_ocid.strip()
        row.fingerprint = fingerprint.strip()
        row.region = region.strip()
        row.updated_by = actor
    db.commit()
    db.refresh(row)
    return row


def rotate_oci_private_key(db: Session, *, pem_text: str) -> EncryptedSecret:
    validate_pem(pem_text)
    enc = encrypt_secret(pem_text.strip())
    existing = (
        db.query(EncryptedSecret)
        .filter(EncryptedSecret.scope == "oci", EncryptedSecret.secret_name == "private_key")
        .order_by(EncryptedSecret.id.desc())
        .first()
    )
    now = datetime.now(UTC)
    if existing:
        existing.ciphertext = enc.ciphertext
        existing.nonce = enc.nonce
        existing.salt = enc.salt
        existing.key_version = enc.key_version
        existing.rotated_at = now
        row = existing
    else:
        row = EncryptedSecret(
            scope="oci",
            secret_name="private_key",
            ciphertext=enc.ciphertext,
            nonce=enc.nonce,
            salt=enc.salt,
            key_version=enc.key_version,
            created_at=now,
            rotated_at=now,
        )
        db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_oci_runtime_credentials(db: Session) -> dict[str, Any]:
    row = db.query(OciIntegration).order_by(OciIntegration.id.desc()).first()
    if not row:
        return {}
    secret = (
        db.query(EncryptedSecret)
        .filter(EncryptedSecret.scope == "oci", EncryptedSecret.secret_name == "private_key")
        .order_by(EncryptedSecret.id.desc())
        .first()
    )
    key_content = None
    if secret:
        key_content = decrypt_secret(secret.ciphertext, secret.nonce, secret.salt)
    return {
        "auth_mode": "direct",
        "user": row.user_ocid,
        "tenancy": row.tenancy_ocid,
        "fingerprint": row.fingerprint,
        "region": row.region,
        "key_content": key_content,
        "status": row.status,
        "last_tested_at": row.last_tested_at.isoformat() if row.last_tested_at else None,
    }


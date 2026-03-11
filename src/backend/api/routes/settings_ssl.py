"""Portal SSL certificate management routes."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Optional

from cryptography import x509
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID
from fastapi import APIRouter, Cookie, Depends, File, Form, HTTPException, Request, UploadFile
from jose import jwt
from sqlalchemy.orm import Session

from core.auth import get_secret_key
from core.config import get_settings
from core.database import ensure_settings_schema, get_db
from core.models import Setting
from core.rbac import resolve_principal
from services.event_logger import audit_event

router = APIRouter()


def _decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, get_secret_key(), algorithms=["HS256"])
    except Exception:
        return None


def _require_admin(
    token: Optional[str] = Cookie(default=None, alias="access_token"),
    db: Session = Depends(get_db),
):
    try:
        principal = resolve_principal(db, token, strict=True)
    except PermissionError:
        raise HTTPException(status_code=401, detail="Not authenticated")
    if principal.role != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")
    return {"sub": principal.username}


def _cert_to_pem_bytes(raw: bytes) -> bytes:
    try:
        cert = x509.load_pem_x509_certificate(raw)
    except Exception:
        cert = x509.load_der_x509_certificate(raw)
    return cert.public_bytes(serialization.Encoding.PEM)


def _private_key_to_pem_bytes(raw: bytes) -> bytes:
    key = serialization.load_pem_private_key(raw, password=None)
    return key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    )


def _leaf_meta(cert_pem: bytes) -> dict:
    cert = x509.load_pem_x509_certificate(cert_pem)
    cn_attr = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)
    return {
        "subject": cert.subject.rfc4514_string(),
        "issuer": cert.issuer.rfc4514_string(),
        "common_name": cn_attr[0].value if cn_attr else None,
        "expires_at": cert.not_valid_after_utc,
    }


@router.get("/settings/portal-ssl")
async def get_portal_ssl_settings(db: Session = Depends(get_db), user=Depends(_require_admin)):
    ensure_settings_schema()
    s = db.query(Setting).filter(Setting.id == 1).one_or_none()
    if not s:
        return {"success": True, "data": {"enabled": False}}
    return {
        "success": True,
        "data": {
            "enabled": bool(getattr(s, "portal_ssl_enabled", False)),
            "mode": getattr(s, "portal_ssl_mode", None),
            "cert_path": getattr(s, "portal_ssl_cert_path", None),
            "key_path": getattr(s, "portal_ssl_key_path", None),
            "chain_path": getattr(s, "portal_ssl_chain_path", None),
            "subject": getattr(s, "portal_ssl_subject", None),
            "issuer": getattr(s, "portal_ssl_issuer", None),
            "expires_at": getattr(s, "portal_ssl_expires_at", None).isoformat() if getattr(s, "portal_ssl_expires_at", None) else None,
            "updated_at": getattr(s, "portal_ssl_updated_at", None).isoformat() if getattr(s, "portal_ssl_updated_at", None) else None,
            "last_error": getattr(s, "portal_ssl_last_error", None),
            "reload_hint": "Run: sudo nginx -t && sudo systemctl reload nginx",
        },
    }


@router.post("/settings/portal-ssl/upload")
async def upload_portal_ssl(
    request: Request,
    cert_file: Optional[UploadFile] = File(default=None),
    key_file: Optional[UploadFile] = File(default=None),
    intermediate_file: Optional[UploadFile] = File(default=None),
    root_file: Optional[UploadFile] = File(default=None),
    pfx_file: Optional[UploadFile] = File(default=None),
    pfx_password: Optional[str] = Form(default=None),
    db: Session = Depends(get_db),
    user=Depends(_require_admin),
):
    ensure_settings_schema()
    s = db.query(Setting).filter(Setting.id == 1).one_or_none()
    if not s:
        raise HTTPException(status_code=500, detail="Settings row missing")

    ssl_dir = Path(get_settings().portal_ssl_dir).expanduser()
    ssl_dir.mkdir(parents=True, exist_ok=True)

    leaf_pem: bytes
    key_pem: bytes
    chain_parts: list[bytes] = []
    mode: str

    try:
        if pfx_file:
            raw = await pfx_file.read()
            pwd = (pfx_password or "").encode("utf-8") if pfx_password else None
            private_key, cert, additional = pkcs12.load_key_and_certificates(raw, pwd)
            if private_key is None or cert is None:
                raise ValueError("PFX file must include certificate and private key")
            leaf_pem = cert.public_bytes(serialization.Encoding.PEM)
            key_pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption(),
            )
            for c in (additional or []):
                chain_parts.append(c.public_bytes(serialization.Encoding.PEM))
            mode = "pfx"
        else:
            if not cert_file or not key_file:
                raise ValueError("Provide cert_file and key_file, or provide pfx_file")
            cert_raw = await cert_file.read()
            key_raw = await key_file.read()
            leaf_pem = _cert_to_pem_bytes(cert_raw)
            key_pem = _private_key_to_pem_bytes(key_raw)
            mode = "pem"

        if intermediate_file:
            chain_parts.append(_cert_to_pem_bytes(await intermediate_file.read()))
        if root_file:
            chain_parts.append(_cert_to_pem_bytes(await root_file.read()))

        # Normalize chain order while keeping user-provided sequence.
        fullchain_pem = leaf_pem + b"".join(chain_parts)

        cert_path = ssl_dir / "portal.fullchain.crt"
        key_path = ssl_dir / "portal.key"
        chain_path = ssl_dir / "portal.chain.crt"

        cert_path.write_bytes(fullchain_pem)
        key_path.write_bytes(key_pem)
        chain_path.write_bytes(b"".join(chain_parts))

        try:
            key_path.chmod(0o600)
            cert_path.chmod(0o644)
            chain_path.chmod(0o644)
        except Exception:
            pass

        meta = _leaf_meta(leaf_pem)
        now = datetime.now(UTC)
        s.portal_ssl_enabled = True
        s.portal_ssl_mode = mode
        s.portal_ssl_cert_path = str(cert_path)
        s.portal_ssl_key_path = str(key_path)
        s.portal_ssl_chain_path = str(chain_path)
        s.portal_ssl_subject = meta.get("subject")
        s.portal_ssl_issuer = meta.get("issuer")
        s.portal_ssl_expires_at = meta.get("expires_at")
        s.portal_ssl_updated_at = now
        s.portal_ssl_last_error = None
        db.commit()

        correlation_id = getattr(request.state, "correlation_id", None)
        audit_event(
            actor=user.get("sub") or "admin",
            action="portal_ssl_uploaded",
            target="portal_ssl",
            correlation_id=correlation_id,
            meta={"mode": mode, "subject": s.portal_ssl_subject, "expires_at": s.portal_ssl_expires_at.isoformat() if s.portal_ssl_expires_at else None},
        )

        return {
            "success": True,
            "data": {
                "enabled": True,
                "mode": mode,
                "cert_path": str(cert_path),
                "key_path": str(key_path),
                "subject": s.portal_ssl_subject,
                "issuer": s.portal_ssl_issuer,
                "expires_at": s.portal_ssl_expires_at.isoformat() if s.portal_ssl_expires_at else None,
                "reload_hint": "Run: sudo nginx -t && sudo systemctl reload nginx",
            },
        }
    except Exception as exc:
        s.portal_ssl_last_error = str(exc)
        s.portal_ssl_updated_at = datetime.now(UTC)
        db.commit()
        raise HTTPException(status_code=400, detail=str(exc))

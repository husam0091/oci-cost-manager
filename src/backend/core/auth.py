"""Auth utilities: password hashing and JWT issuance/verification."""
import os
from datetime import UTC, datetime, timedelta
from typing import Optional

from jose import jwt, JWTError
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_secret_key() -> str:
    return os.environ.get("APP_SECRET", "dev-secret-change-me")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def create_access_token(subject: str, expires_minutes: int = 60) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": subject,
        "exp": now + timedelta(minutes=expires_minutes),
        "iat": now,
        "nbf": now,
    }
    return jwt.encode(payload, get_secret_key(), algorithm="HS256")


def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, get_secret_key(), algorithms=["HS256"])
    except JWTError:
        return None

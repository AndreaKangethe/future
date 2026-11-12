from datetime import UTC, datetime, timedelta

from argon2 import PasswordHasher
from jose import jwt

from app.core.config import get_settings

_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except Exception:
        return False


def create_token(subject: str) -> str:
    now = datetime.now(UTC)
    return jwt.encode(
        {"sub": subject, "iat": now, "exp": now + timedelta(hours=8)},
        get_settings().jwt_secret,
        algorithm="HS256",
    )

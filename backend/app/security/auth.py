"""JWT + bcrypt. Passwords are never stored in plaintext."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

from app.config import get_settings

ROLE_PERMISSIONS: dict[str, set[str]] = {
    "admin": {
        "change:write",
        "change:read",
        "policy:write",
        "policy:read",
        "approval:write",
        "approval:read",
        "audit:read",
        "admin",
        "research",
        "recovery",
    },
    "engineer": {"change:write", "change:read", "approval:read", "policy:read", "recovery"},
    "operator": {"change:write", "change:read", "approval:read"},
    "analyst": {"change:read", "policy:read", "audit:read", "research"},
    "auditor": {"change:read", "audit:read", "approval:read"},
    "researcher": {"change:read", "policy:read", "research", "change:write"},
}


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def create_token(username: str, role: str) -> str:
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    return jwt.encode(
        {"sub": username, "role": role, "exp": expire},
        settings.secret_key,
        algorithm=settings.jwt_algorithm,
    )


def decode_token(token: str) -> dict:
    settings = get_settings()
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise ValueError("Invalid token") from exc


def has_permission(role: str, permission: str) -> bool:
    return permission in ROLE_PERMISSIONS.get(role, set())

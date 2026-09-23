from __future__ import annotations

from collections.abc import Generator

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.persistence.database import get_session_factory
from app.security.auth import decode_token, has_permission
from app.services.runtime import AssuranceRuntime, get_runtime

oauth2 = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def db_session() -> Generator[Session, None, None]:
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def runtime_dep() -> AssuranceRuntime:
    return get_runtime()


def current_user(token: str | None = Depends(oauth2)) -> dict:
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = decode_token(token)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="Invalid token") from exc
    return {"username": payload.get("sub"), "role": payload.get("role")}


def require(permission: str):
    def _inner(user: dict = Depends(current_user)) -> dict:
        if not has_permission(user["role"], permission):
            raise HTTPException(status_code=403, detail="Insufficient role")
        return user

    return _inner

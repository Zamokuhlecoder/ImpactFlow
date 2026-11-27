"""Stdlib password hashing, signed tokens and the RBAC permission matrix."""

import base64
import hashlib
import hmac
import json
import secrets
import time
from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.database.session import get_db_session
from app.models import User

ROLES = ("admin", "data_owner", "data_steward", "data_engineer", "viewer")
_ALL = {
    "dataset.view", "dataset.upload", "metadata.modify", "quality.rule.manage", "quality.run",
    "quality.issue.manage", "pipeline.execute", "sensitive.view", "users.manage", "audit.view",
    "policy.manage", "access.request", "access.approve",
}
PERMISSIONS: dict[str, frozenset[str]] = {
    "admin": frozenset(_ALL),
    "data_owner": frozenset(
        {"dataset.view", "metadata.modify", "sensitive.view", "access.request", "access.approve"}
    ),
    "data_steward": frozenset(
        {"dataset.view", "metadata.modify", "quality.rule.manage", "quality.run",
         "quality.issue.manage", "access.request"}
    ),
    "data_engineer": frozenset(
        {"dataset.view", "dataset.upload", "pipeline.execute", "quality.rule.manage",
         "quality.run", "quality.issue.manage", "access.request"}
    ),
    "viewer": frozenset({"dataset.view", "access.request"}),
}
SERVICE_PERMISSIONS = frozenset({"quality.run", "dataset.view"})
_SCRYPT = {"n": 2**14, "r": 8, "p": 1}


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, **_SCRYPT)
    return f"scrypt${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, salt, digest = stored.split("$")
        if scheme != "scrypt":
            return False
        candidate = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), **_SCRYPT)
        return hmac.compare_digest(candidate, bytes.fromhex(digest))
    except ValueError:
        return False


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def create_token(user_id: UUID, settings: Settings, now: float | None = None) -> str:
    if settings.auth_secret_key is None:
        raise RuntimeError("Authentication secret is not configured.")
    issued = time.time() if now is None else now
    body = _b64(
        json.dumps(
            {"sub": str(user_id), "exp": int(issued + settings.auth_token_ttl_minutes * 60)}
        ).encode()
    )
    key = settings.auth_secret_key.get_secret_value().encode()
    return f"{body}.{_b64(hmac.new(key, body.encode(), hashlib.sha256).digest())}"


def read_token(token: str, settings: Settings, now: float | None = None) -> UUID | None:
    if settings.auth_secret_key is None:
        return None
    try:
        body, signature = token.split(".")
        key = settings.auth_secret_key.get_secret_value().encode()
        expected = _b64(hmac.new(key, body.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(expected, signature):
            return None
        claims = json.loads(_unb64(body))
        if claims["exp"] < (time.time() if now is None else now):
            return None
        return UUID(claims["sub"])
    except (ValueError, KeyError, TypeError):
        return None


@dataclass(frozen=True)
class Principal:
    id: UUID | None
    label: str
    role: str
    permissions: frozenset[str]

    def has(self, permission: str) -> bool:
        return permission in self.permissions


def get_principal(request: Request, session: Annotated[Session, Depends(get_db_session)]) -> Principal:
    settings: Settings = request.app.state.settings
    service_token = request.headers.get("X-Governance-Service-Token")
    if service_token is not None:
        expected = settings.governance_service_token
        if expected and hmac.compare_digest(service_token, expected.get_secret_value()):
            return Principal(None, "service:airflow", "service", SERVICE_PERMISSIONS)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid service token.")
    header = request.headers.get("Authorization", "")
    if not header.lower().startswith("bearer "):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "Authentication required.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_id = read_token(header[7:].strip(), settings)
    user = session.get(User, user_id) if user_id else None
    if user is None or not user.is_active or user.role not in PERMISSIONS:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "Invalid or expired session.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return Principal(user.id, user.email, user.role, PERMISSIONS[user.role])


CurrentPrincipal = Annotated[Principal, Depends(get_principal)]


def require(permission: str):
    def dependency(principal: CurrentPrincipal) -> Principal:
        if not principal.has(permission):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "You do not have permission.")
        return principal

    return dependency

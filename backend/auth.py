"""Auth primitives: password hashing + JWT + FastAPI dependencies.

Step 5 of Phase 4. Co-located in one module rather than spread across
several so callers see the whole auth surface at a glance.

Token contract (HS256, signed with settings.jwt_secret):
    iat, exp, sub (= user_id), org_id (= active organization_id)

Cookie: HttpOnly, SameSite=Lax, 7-day Max-Age. Set by the auth routes
via the helper in `backend/routes/auth.py`. Frontend never touches the
JWT directly.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.db import get_db
from backend.models import Organization, OrganizationMember, User
from backend.settings import Settings, get_settings


class AuthError(Exception):
    """Raised internally for any token / membership failure. Routes convert to HTTPException."""


_hasher = PasswordHasher()  # argon2id with library defaults — meets Phase 3 §6.1


# ---------------------------------------------------------------------------
# Passwords (argon2id)
# ---------------------------------------------------------------------------


def hash_password(plain: str) -> str:
    """Hash with argon2id. The output encodes algorithm + params + salt."""
    return _hasher.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Constant-time verify. Returns False on any mismatch; never raises."""
    try:
        _hasher.verify(hashed, plain)
        return True
    except (VerifyMismatchError, InvalidHashError):
        return False


def needs_rehash(hashed: str) -> bool:
    """True when the stored hash uses outdated params and should be replaced."""
    try:
        return _hasher.check_needs_rehash(hashed)
    except InvalidHashError:
        return True


# ---------------------------------------------------------------------------
# JWT
# ---------------------------------------------------------------------------


def encode_token(
    *,
    user_id: str,
    org_id: str,
    settings: Settings,
    ttl_seconds: int | None = None,
) -> str:
    """Sign a session token. Use settings.jwt_secret; HS256 unless overridden."""
    if not settings.jwt_secret:
        raise RuntimeError("JWT_SECRET is not set — refusing to issue tokens")
    now = datetime.now(tz=timezone.utc)
    ttl = ttl_seconds if ttl_seconds is not None else settings.session_max_age_seconds
    payload: dict[str, Any] = {
        "sub": user_id,
        "org_id": org_id,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=ttl)).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str, settings: Settings) -> dict[str, Any]:
    """Verify signature + expiry. Raises AuthError on any failure."""
    if not settings.jwt_secret:
        raise AuthError("JWT_SECRET not configured")
    try:
        return jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
    except jwt.ExpiredSignatureError as exc:
        raise AuthError("session expired") from exc
    except jwt.InvalidTokenError as exc:
        raise AuthError(f"invalid session: {exc}") from exc


# ---------------------------------------------------------------------------
# FastAPI dependencies
# ---------------------------------------------------------------------------


def _unauthenticated() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={
            "error": {
                "code": "UNAUTHENTICATED",
                "message_en": "Authentication required.",
                "message_ka": "ავტორიზაცია აუცილებელია.",
            }
        },
    )


def _forbidden_org() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={
            "error": {
                "code": "FORBIDDEN_ORG",
                "message_en": "You don't belong to this organization.",
                "message_ka": "თქვენ არ ხართ ამ ორგანიზაციის წევრი.",
            }
        },
    )


def _read_session_token(request: Request, settings: Settings) -> str:
    cookie = request.cookies.get(settings.session_cookie_name)
    if not cookie:
        raise _unauthenticated()
    return cookie


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> User:
    """FastAPI dependency. Reads the session cookie, verifies JWT, returns the User row."""
    token = _read_session_token(request, settings)
    try:
        payload = decode_token(token, settings)
    except AuthError as exc:
        raise _unauthenticated() from exc

    user_id = payload.get("sub")
    if not user_id or not isinstance(user_id, str):
        raise _unauthenticated()

    user = db.get(User, user_id)
    if user is None:
        raise _unauthenticated()
    return user


def get_current_org(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> Organization:
    """FastAPI dependency. Returns the active org from the token, verifying membership."""
    token = _read_session_token(request, settings)
    try:
        payload = decode_token(token, settings)
    except AuthError as exc:
        raise _unauthenticated() from exc

    org_id = payload.get("org_id")
    if not org_id or not isinstance(org_id, str):
        raise _unauthenticated()

    org = db.get(Organization, org_id)
    if org is None:
        raise _unauthenticated()

    membership = db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == org.id,
            OrganizationMember.user_id == current_user.id,
        )
    ).scalar_one_or_none()
    if membership is None:
        raise _forbidden_org()

    return org

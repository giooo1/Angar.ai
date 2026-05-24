"""Auth-path API endpoints: register / login / logout / me.

Phase 4 step 5. Cookie-based session: the JWT lives in an HttpOnly
cookie set on register and login responses. The frontend never sees
the token directly.
"""

from __future__ import annotations

import hashlib
import re
import secrets
from datetime import datetime, timedelta, timezone

from email_validator import EmailNotValidError, validate_email
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.rate_limit import limiter

from backend.api_schemas import (
    ApiError,
    ErrorResponse,
    LoginRequest,
    OrganizationDTO,
    RegisterRequest,
    RequestPasswordResetRequest,
    ResetPasswordRequest,
    SessionResponse,
    UserDTO,
    VerifyEmailRequest,
)
from backend.auth import (
    encode_token,
    get_current_org,
    get_current_user,
    hash_password,
    verify_password,
)
from backend.db import get_db
from backend.email import send_password_reset_email, send_verification_email
from backend.models import EmailToken, Organization, OrganizationMember, User
from backend.settings import PLAN_QUOTAS, Settings, get_settings

router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_MIN_PASSWORD_LEN = 8


def _bilingual(code: str, en: str, ka: str) -> ErrorResponse:
    return ErrorResponse(error=ApiError(code=code, message_en=en, message_ka=ka))


def _validate_password(password: str) -> None:
    if len(password) < _MIN_PASSWORD_LEN:
        raise HTTPException(
            status_code=400,
            detail=_bilingual(
                "WEAK_PASSWORD",
                f"Password must be at least {_MIN_PASSWORD_LEN} characters.",
                f"პაროლი უნდა იყოს მინიმუმ {_MIN_PASSWORD_LEN} სიმბოლო.",
            ).model_dump(),
        )
    if not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
        raise HTTPException(
            status_code=400,
            detail=_bilingual(
                "WEAK_PASSWORD",
                "Password must include at least one letter and one digit.",
                "პაროლი უნდა შეიცავდეს მინიმუმ ერთ ასოს და ერთ ციფრს.",
            ).model_dump(),
        )


def _normalize_email(raw: str) -> str:
    try:
        info = validate_email(raw, check_deliverability=False)
        return info.normalized.lower()
    except EmailNotValidError as exc:
        raise HTTPException(
            status_code=400,
            detail=_bilingual(
                "INVALID_EMAIL",
                f"Email is not valid: {exc}",
                "ელფოსტა არასწორია.",
            ).model_dump(),
        ) from exc


def _session_response(user: User, org: Organization) -> SessionResponse:
    return SessionResponse(
        user=UserDTO(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            locale=user.locale,
            email_verified_at=user.email_verified_at,
        ),
        organization=OrganizationDTO(
            id=org.id,
            name=org.name,
            plan=org.plan,
            monthly_extraction_quota=org.monthly_extraction_quota,
            monthly_extractions_used=org.monthly_extractions_used,
            quota_reset_at=org.quota_reset_at,
        ),
    )


def _set_session_cookie(response: Response, token: str, settings: Settings) -> None:
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        max_age=settings.session_max_age_seconds,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,  # type: ignore[arg-type]
        path="/",
    )


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _new_email_token(
    user: User, purpose: str, ttl_hours: int, db: Session
) -> str:
    """Mint a fresh one-time token; persist the hash, return the raw value.

    Caller is responsible for db.commit() — the token row is added but
    not committed so we can fold it into the register / request-reset
    transaction.
    """
    raw = secrets.token_urlsafe(48)
    token = EmailToken(
        user_id=user.id,
        purpose=purpose,
        token_hash=_hash_token(raw),
        expires_at=datetime.now(tz=timezone.utc) + timedelta(hours=ttl_hours),
    )
    db.add(token)
    return raw


def _consume_token(
    raw_token: str, purpose: str, db: Session
) -> tuple[User, EmailToken]:
    """Look up the token; raise 400 if missing / expired / used."""
    h = _hash_token(raw_token)
    token = db.execute(
        select(EmailToken)
        .where(EmailToken.token_hash == h, EmailToken.purpose == purpose)
    ).scalar_one_or_none()
    if token is None or token.used_at is not None:
        raise HTTPException(
            status_code=400,
            detail=_bilingual(
                "INVALID_TOKEN",
                "This link is invalid or has already been used.",
                "ბმული არასწორია ან უკვე გამოყენებულია.",
            ).model_dump(),
        )
    expires_at = token.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(tz=timezone.utc):
        raise HTTPException(
            status_code=400,
            detail=_bilingual(
                "EXPIRED_TOKEN",
                "This link has expired. Request a new one.",
                "ბმულის ვადა ამოწურულია — მოითხოვეთ ახალი.",
            ).model_dump(),
        )
    user = db.get(User, token.user_id)
    if user is None:
        # Defensive: shouldn't happen given the FK.
        raise HTTPException(
            status_code=400,
            detail=_bilingual(
                "INVALID_TOKEN",
                "This link is invalid.",
                "ბმული არასწორია.",
            ).model_dump(),
        )
    return user, token


def _clear_session_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        key=settings.session_cookie_name,
        path="/",
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,  # type: ignore[arg-type]
    )


# ---------------------------------------------------------------------------
# POST /auth/register
# ---------------------------------------------------------------------------


@router.post(
    "/auth/register",
    status_code=status.HTTP_201_CREATED,
    response_model=SessionResponse,
    responses={
        400: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
    },
)
@limiter.limit("3/hour")
def register(
    request: Request,
    body: RegisterRequest,
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> SessionResponse:
    email = _normalize_email(body.email)
    _validate_password(body.password)

    if not body.organization_name.strip():
        raise HTTPException(
            status_code=400,
            detail=_bilingual(
                "INVALID_ORG_NAME",
                "Organization name is required.",
                "ორგანიზაციის სახელი აუცილებელია.",
            ).model_dump(),
        )

    existing = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail=_bilingual(
                "EMAIL_TAKEN",
                "An account with this email already exists.",
                "ანგარიში ამ ელფოსტით უკვე არსებობს.",
            ).model_dump(),
        )

    user = User(
        email=email,
        password_hash=hash_password(body.password),
        full_name=body.full_name,
        last_login_at=datetime.now(tz=timezone.utc),
    )
    # New orgs always start on "free"; quota field set explicitly so the
    # row carries it before flush.
    org = Organization(
        name=body.organization_name.strip(),
        plan="free",
        monthly_extraction_quota=PLAN_QUOTAS["free"],
        monthly_extractions_used=0,
        quota_reset_at=datetime.now(tz=timezone.utc) + timedelta(days=30),
    )
    db.add(user)
    db.add(org)
    db.flush()  # ids populated

    db.add(
        OrganizationMember(
            organization_id=org.id, user_id=user.id, role="owner"
        )
    )
    # Verification token — raw value goes in the email; only the hash is stored.
    raw_verify_token = _new_email_token(
        user, "verify", settings.email_verify_token_ttl_hours, db
    )
    db.commit()
    db.refresh(user)
    db.refresh(org)

    # Fire-and-forget; _send swallows errors so signup never breaks on
    # Resend hiccups. In tests resend_api_key is empty and this no-ops.
    send_verification_email(user, raw_verify_token, settings)

    token = encode_token(user_id=user.id, org_id=org.id, settings=settings)
    _set_session_cookie(response, token, settings)

    return _session_response(user, org)


# ---------------------------------------------------------------------------
# POST /auth/login
# ---------------------------------------------------------------------------


@router.post(
    "/auth/login",
    response_model=SessionResponse,
    responses={
        401: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
    },
)
@limiter.limit("5/minute")
def login(
    request: Request,
    body: LoginRequest,
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> SessionResponse:
    email = _normalize_email(body.email)
    user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()

    if user is None or not verify_password(body.password, user.password_hash):
        # Same error for unknown email vs wrong password — no enumeration.
        raise HTTPException(
            status_code=401,
            detail=_bilingual(
                "INVALID_CREDENTIALS",
                "Email or password is incorrect.",
                "ელფოსტა ან პაროლი არასწორია.",
            ).model_dump(),
        )

    membership = db.execute(
        select(OrganizationMember).where(OrganizationMember.user_id == user.id)
    ).scalars().first()
    if membership is None:
        # Defensive: registration always creates a membership; this would
        # only happen if a user was manually deleted from the org.
        raise HTTPException(
            status_code=403,
            detail=_bilingual(
                "NO_ORG",
                "Your account is not attached to an organization.",
                "თქვენი ანგარიში არ არის მიბმული ორგანიზაციასთან.",
            ).model_dump(),
        )

    org = db.get(Organization, membership.organization_id)
    if org is None:
        raise HTTPException(
            status_code=403,
            detail=_bilingual(
                "ORG_MISSING",
                "Your organization no longer exists.",
                "ორგანიზაცია აღარ არსებობს.",
            ).model_dump(),
        )

    user.last_login_at = datetime.now(tz=timezone.utc)
    db.commit()

    token = encode_token(user_id=user.id, org_id=org.id, settings=settings)
    _set_session_cookie(response, token, settings)

    return _session_response(user, org)


# ---------------------------------------------------------------------------
# POST /auth/logout
# ---------------------------------------------------------------------------


@router.post(
    "/auth/logout",
    status_code=status.HTTP_204_NO_CONTENT,
)
def logout(
    response: Response,
    settings: Settings = Depends(get_settings),
) -> Response:
    _clear_session_cookie(response, settings)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


# ---------------------------------------------------------------------------
# GET /me
# ---------------------------------------------------------------------------


@router.get(
    "/me",
    response_model=SessionResponse,
    responses={401: {"model": ErrorResponse}},
)
def me(
    current_user: User = Depends(get_current_user),
    current_org: Organization = Depends(get_current_org),
) -> SessionResponse:
    return _session_response(current_user, current_org)


# ---------------------------------------------------------------------------
# Email verification + password reset (WS4)
# ---------------------------------------------------------------------------


@router.post(
    "/auth/verify-email",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={400: {"model": ErrorResponse}, 429: {"model": ErrorResponse}},
)
@limiter.limit("10/minute")
def verify_email(
    request: Request,
    body: VerifyEmailRequest,
    db: Session = Depends(get_db),
) -> Response:
    user, token = _consume_token(body.token, "verify", db)
    user.email_verified_at = datetime.now(tz=timezone.utc)
    token.used_at = user.email_verified_at
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/auth/request-password-reset",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={429: {"model": ErrorResponse}},
)
@limiter.limit("3/hour")
def request_password_reset(
    request: Request,
    body: RequestPasswordResetRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> Response:
    """Send a reset link if the address belongs to a real user.

    Returns 204 regardless of whether the email matches, so the response
    can't be used as an account-enumeration oracle.
    """
    try:
        email = _normalize_email(body.email)
    except HTTPException:
        # Don't leak validation errors; still 204.
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if user is not None:
        raw = _new_email_token(
            user, "reset", settings.email_reset_token_ttl_hours, db
        )
        db.commit()
        send_password_reset_email(user, raw, settings)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/auth/reset-password",
    response_model=SessionResponse,
    responses={
        400: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
    },
)
@limiter.limit("5/hour")
def reset_password(
    request: Request,
    body: ResetPasswordRequest,
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> SessionResponse:
    user, token = _consume_token(body.token, "reset", db)
    _validate_password(body.new_password)

    user.password_hash = hash_password(body.new_password)
    user.last_login_at = datetime.now(tz=timezone.utc)
    token.used_at = datetime.now(tz=timezone.utc)
    # Invalidate any other outstanding reset tokens for this user.
    other_reset_tokens = db.execute(
        select(EmailToken).where(
            EmailToken.user_id == user.id,
            EmailToken.purpose == "reset",
            EmailToken.used_at.is_(None),
        )
    ).scalars().all()
    for t in other_reset_tokens:
        t.used_at = datetime.now(tz=timezone.utc)

    membership = db.execute(
        select(OrganizationMember).where(OrganizationMember.user_id == user.id)
    ).scalars().first()
    if membership is None:
        db.commit()
        raise HTTPException(
            status_code=400,
            detail=_bilingual(
                "NO_ORG",
                "Your account is not attached to an organization.",
                "თქვენი ანგარიში არ არის მიბმული ორგანიზაციასთან.",
            ).model_dump(),
        )

    org = db.get(Organization, membership.organization_id)
    if org is None:
        db.commit()
        raise HTTPException(
            status_code=400,
            detail=_bilingual(
                "ORG_MISSING",
                "Your organization no longer exists.",
                "ორგანიზაცია აღარ არსებობს.",
            ).model_dump(),
        )

    db.commit()
    db.refresh(user)

    jwt = encode_token(user_id=user.id, org_id=org.id, settings=settings)
    _set_session_cookie(response, jwt, settings)
    return _session_response(user, org)

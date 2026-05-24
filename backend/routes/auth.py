"""Auth-path API endpoints: register / login / logout / me.

Phase 4 step 5. Cookie-based session: the JWT lives in an HttpOnly
cookie set on register and login responses. The frontend never sees
the token directly.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

from email_validator import EmailNotValidError, validate_email
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.rate_limit import limiter

from backend.api_schemas import (
    ApiError,
    ErrorResponse,
    LoginRequest,
    OrganizationDTO,
    RegisterRequest,
    SessionResponse,
    UserDTO,
)
from backend.auth import (
    encode_token,
    get_current_org,
    get_current_user,
    hash_password,
    verify_password,
)
from backend.db import get_db
from backend.models import Organization, OrganizationMember, User
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
    db.commit()
    db.refresh(user)
    db.refresh(org)

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

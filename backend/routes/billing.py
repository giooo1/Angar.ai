"""Billing endpoints (Phase 4.5 WS5).

Two user-facing endpoints (Checkout + Portal) and one Stripe-facing
endpoint (Webhook). The webhook reads the RAW body (not the parsed
JSON) because Stripe's signature is computed over the raw bytes.
"""

from __future__ import annotations

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.api_schemas import ApiError, ErrorResponse
from backend.auth import get_current_org, get_current_user
from backend.db import get_db
from backend.models import Organization, User
from backend.rate_limit import limiter
from backend.settings import PLAN_QUOTAS, Settings, get_settings
from backend.stripe_service import (
    create_billing_portal_session,
    create_checkout_session,
    handle_webhook,
)

router = APIRouter()


def _bilingual(code: str, en: str, ka: str) -> dict:
    return ErrorResponse(error=ApiError(code=code, message_en=en, message_ka=ka)).model_dump()


class CheckoutRequest(BaseModel):
    plan: str  # "pro" | "business"


class CheckoutResponse(BaseModel):
    url: str


@router.post(
    "/billing/checkout",
    response_model=CheckoutResponse,
    responses={
        400: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
    },
)
@limiter.limit("10/hour")
def billing_checkout(
    request: Request,
    body: CheckoutRequest,
    current_user: User = Depends(get_current_user),
    current_org: Organization = Depends(get_current_org),
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
) -> CheckoutResponse:
    if current_user.email_verified_at is None:
        raise HTTPException(
            status_code=403,
            detail=_bilingual(
                "EMAIL_NOT_VERIFIED",
                "Verify your email before subscribing.",
                "გამოწერამდე დაადასტურეთ ელფოსტა.",
            ),
        )
    if body.plan not in PLAN_QUOTAS or body.plan == "free":
        raise HTTPException(
            status_code=400,
            detail=_bilingual(
                "INVALID_PLAN",
                f"Unknown plan '{body.plan}'.",
                f"გეგმა '{body.plan}' უცნობია.",
            ),
        )
    try:
        url = create_checkout_session(
            org=current_org, owner=current_user, plan=body.plan, settings=settings
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail=_bilingual(
                "BILLING_UNCONFIGURED",
                str(exc),
                "გადახდის სისტემა გაუმართავია — დაუკავშირდით მხარდაჭერას.",
            ),
        )
    db.commit()  # persist stripe_customer_id if newly created
    return CheckoutResponse(url=url)


@router.post(
    "/billing/portal",
    response_model=CheckoutResponse,
    responses={
        403: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
    },
)
@limiter.limit("10/hour")
def billing_portal(
    request: Request,
    current_user: User = Depends(get_current_user),
    current_org: Organization = Depends(get_current_org),
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
) -> CheckoutResponse:
    if not current_org.stripe_customer_id:
        raise HTTPException(
            status_code=400,
            detail=_bilingual(
                "NO_STRIPE_CUSTOMER",
                "This account has no billing record yet — start a subscription first.",
                "ანგარიშზე გადახდის ჩანაწერი ჯერ არ არსებობს.",
            ),
        )
    url = create_billing_portal_session(
        org=current_org, owner=current_user, settings=settings
    )
    db.commit()
    return CheckoutResponse(url=url)


@router.post(
    "/webhooks/stripe",
    status_code=status.HTTP_200_OK,
)
async def stripe_webhook(
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict[str, str]:
    """Receive + dispatch Stripe webhooks.

    IMPORTANT: read the raw body — Stripe's signature is computed over
    the bytes Stripe sent, including whitespace. We DO NOT call
    request.json() before construct_event because that would re-encode.
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")
    if not settings.stripe_webhook_secret:
        # In dev / tests without a secret configured, refuse rather than
        # silently accept unverified events.
        raise HTTPException(
            status_code=503,
            detail=_bilingual(
                "WEBHOOK_UNCONFIGURED",
                "Webhook secret not configured.",
                "ვებჰუკის საიდუმლო არ არის გამართული.",
            ),
        )
    try:
        # construct_event raises on tampered signature; we discard the
        # StripeObject and re-parse the bytes into a plain dict so the
        # dispatch helpers work with predictable dict subscript shapes.
        stripe.Webhook.construct_event(
            payload=payload,
            sig_header=sig_header,
            secret=settings.stripe_webhook_secret,
        )
    except stripe.error.SignatureVerificationError:  # type: ignore[attr-defined]
        raise HTTPException(status_code=400, detail="invalid signature")
    except ValueError:
        raise HTTPException(status_code=400, detail="invalid payload")

    import json

    event_dict = json.loads(payload)
    handle_webhook(event_dict, db, settings)
    return {"received": "ok"}

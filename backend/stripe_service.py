"""Stripe integration (Phase 4.5 WS5).

Three responsibilities:

  1. ensure_customer(org)         — look up or create the Stripe Customer.
  2. create_checkout_session(...) — opens a paywall for Pro / Business.
  3. handle_webhook(event, db)    — dispatch event types to handlers,
                                    with idempotency via WebhookEvent.

Webhook handlers MUTATE org plan/quota and send receipts. They are
called from the route layer AFTER signature verification — see
`backend/routes/billing.py` for the construct_event boundary.

Plan→Price-id mapping flows top-down: Stripe holds the canonical Price
id; we read it from settings (env). On `checkout.session.completed` we
match the Price id back to a plan slug to know which quota tier to apply.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import stripe
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.email import send_billing_receipt
from backend.models import Organization, OrganizationMember, User, WebhookEvent
from backend.settings import PLAN_QUOTAS, Settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Customer + Checkout
# ---------------------------------------------------------------------------


def _api_key(settings: Settings) -> None:
    """The Stripe SDK reads `stripe.api_key` as a module-level global.
    Call this before every SDK invocation to make sure the right key is
    set even if multiple tests or settings overrides come into play."""
    stripe.api_key = settings.stripe_secret_key


def ensure_customer(org: Organization, owner: User, settings: Settings) -> str:
    """Return the org's Stripe Customer id, creating one if missing."""
    _api_key(settings)
    if org.stripe_customer_id:
        return org.stripe_customer_id
    customer = stripe.Customer.create(
        email=owner.email,
        name=org.name,
        metadata={"angar_org_id": org.id},
    )
    org.stripe_customer_id = customer.id
    return customer.id


def _price_id_for_plan(plan: str, settings: Settings) -> str | None:
    if plan == "pro":
        return settings.stripe_price_id_pro
    if plan == "business":
        return settings.stripe_price_id_business
    return None


def create_checkout_session(
    *,
    org: Organization,
    owner: User,
    plan: str,
    settings: Settings,
) -> str:
    """Return the Stripe Checkout URL the frontend should redirect to."""
    if plan not in ("pro", "business"):
        raise ValueError(f"invalid plan: {plan}")
    price_id = _price_id_for_plan(plan, settings)
    if not price_id:
        raise RuntimeError(
            f"stripe_price_id_{plan} not configured. "
            f"Set it in .env after creating the Price in your Stripe dashboard."
        )

    customer_id = ensure_customer(org, owner, settings)
    origin = settings.frontend_origin.rstrip("/")
    session = stripe.checkout.Session.create(
        customer=customer_id,
        mode="subscription",
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=f"{origin}/settings/billing/success?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{origin}/settings/billing",
        metadata={"angar_org_id": org.id, "plan": plan},
        subscription_data={"metadata": {"angar_org_id": org.id, "plan": plan}},
    )
    return session.url  # type: ignore[return-value]


def create_billing_portal_session(
    *, org: Organization, owner: User, settings: Settings
) -> str:
    """Open the Stripe-hosted Customer Portal for plan/payment management."""
    customer_id = ensure_customer(org, owner, settings)
    portal = stripe.billing_portal.Session.create(
        customer=customer_id,
        return_url=f"{settings.frontend_origin.rstrip('/')}/settings/billing",
    )
    return portal.url  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Webhooks
# ---------------------------------------------------------------------------


_PLAN_BY_PRICE_FALLBACK = "pro"  # If we can't match the Price id, fall back.


def _plan_from_price(price_id: str | None, settings: Settings) -> str | None:
    if price_id == settings.stripe_price_id_pro:
        return "pro"
    if price_id == settings.stripe_price_id_business:
        return "business"
    return None


def _apply_plan_to_org(org: Organization, plan: str) -> None:
    """Set the org's plan + reset its rolling-window counter."""
    org.plan = plan
    org.monthly_extraction_quota = PLAN_QUOTAS[plan]
    org.monthly_extractions_used = 0
    org.quota_reset_at = datetime.now(tz=timezone.utc) + timedelta(days=30)


def _find_org_by_customer(customer_id: str | None, db: Session) -> Organization | None:
    if not customer_id:
        return None
    return (
        db.query(Organization)
        .filter(Organization.stripe_customer_id == customer_id)
        .one_or_none()
    )


def _find_owner(org: Organization, db: Session) -> User | None:
    membership = (
        db.query(OrganizationMember)
        .filter(OrganizationMember.organization_id == org.id, OrganizationMember.role == "owner")
        .first()
    )
    if membership is None:
        return None
    return db.get(User, membership.user_id)


def handle_webhook(
    event: dict[str, Any], db: Session, settings: Settings
) -> None:
    """Idempotent webhook dispatch. Caller has already verified the signature.

    Inserts an idempotency row keyed by event id; if the row already
    exists the handler short-circuits. After dispatch the row's
    `processed_at` is stamped.

    Unhandled event types are recorded and silently acked (Stripe expects
    2xx for anything we don't care about, otherwise it keeps retrying).
    """
    event_id: str = event["id"]
    event_type: str = event["type"]
    record = WebhookEvent(id=event_id, type=event_type)
    db.add(record)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        logger.info("stripe webhook %s already processed; ack-only", event_id)
        return

    try:
        handler = _DISPATCH.get(event_type)
        if handler is None:
            logger.info("stripe webhook %s (%s) not handled", event_id, event_type)
        else:
            handler(event, db, settings)
        record.processed_at = datetime.now(tz=timezone.utc)
        db.commit()
    except Exception:
        # We DON'T re-raise: the event is recorded and we don't want
        # Stripe to retry. We DO log loudly so an operator notices.
        logger.exception("stripe webhook %s (%s) handler crashed", event_id, event_type)
        db.commit()


# --- Per-event handlers ----------------------------------------------------


def _on_checkout_completed(event: dict[str, Any], db: Session, settings: Settings) -> None:
    data = event["data"]["object"]
    customer_id = data.get("customer")
    org = _find_org_by_customer(customer_id, db)
    if org is None:
        logger.warning(
            "stripe checkout.session.completed for unknown customer=%s; ack-only",
            customer_id,
        )
        return

    org.stripe_subscription_id = data.get("subscription")

    plan: str | None = None
    metadata = data.get("metadata") or {}
    if metadata.get("plan") in PLAN_QUOTAS:
        plan = metadata["plan"]
    if plan is None:
        # Fall back to looking up the line items via Stripe.
        try:
            _api_key(settings)
            session = stripe.checkout.Session.retrieve(
                data["id"], expand=["line_items"]
            )
            for li in session.line_items.data:  # type: ignore[attr-defined]
                plan = _plan_from_price(li.price.id, settings)
                if plan:
                    break
        except Exception:  # noqa: BLE001
            logger.exception("could not retrieve checkout line items")
    if plan is None:
        plan = _PLAN_BY_PRICE_FALLBACK
    _apply_plan_to_org(org, plan)


def _on_subscription_updated(event: dict[str, Any], db: Session, settings: Settings) -> None:
    data = event["data"]["object"]
    org = _find_org_by_customer(data.get("customer"), db)
    if org is None:
        return
    # Find the first item's Price; assumes single-line subscriptions
    # (which is what our Checkout creates).
    items = (data.get("items") or {}).get("data") or []
    if not items:
        return
    price_id = items[0].get("price", {}).get("id")
    plan = _plan_from_price(price_id, settings)
    if plan is None:
        logger.warning("subscription.updated with unrecognized price=%s", price_id)
        return
    if plan != org.plan:
        _apply_plan_to_org(org, plan)
    org.stripe_subscription_id = data.get("id") or org.stripe_subscription_id


def _on_subscription_deleted(event: dict[str, Any], db: Session, settings: Settings) -> None:
    data = event["data"]["object"]
    org = _find_org_by_customer(data.get("customer"), db)
    if org is None:
        return
    # Revert to free immediately. (Some products defer to period-end; we
    # don't yet — keeps the demo simple.)
    _apply_plan_to_org(org, "free")
    org.stripe_subscription_id = None


def _on_invoice_payment_succeeded(event: dict[str, Any], db: Session, settings: Settings) -> None:
    data = event["data"]["object"]
    org = _find_org_by_customer(data.get("customer"), db)
    if org is None:
        return
    owner = _find_owner(org, db)
    if owner is None:
        return
    amount = data.get("amount_paid") or 0
    currency = (data.get("currency") or "usd").upper()
    period = data.get("period") or {}
    start_ts = period.get("start") or data.get("period_start") or 0
    end_ts = period.get("end") or data.get("period_end") or 0
    start = datetime.fromtimestamp(start_ts, tz=timezone.utc)
    end = datetime.fromtimestamp(end_ts, tz=timezone.utc)
    amount_display = f"{amount / 100:.2f} {currency}"
    send_billing_receipt(
        user=owner,
        amount_display=amount_display,
        period_start=start,
        period_end=end,
        plan=org.plan,
        settings=settings,
    )


def _on_invoice_payment_failed(event: dict[str, Any], db: Session, settings: Settings) -> None:
    data = event["data"]["object"]
    org = _find_org_by_customer(data.get("customer"), db)
    if org is None:
        return
    # We don't downgrade immediately — Stripe will retry and eventually
    # cancel the subscription, which triggers customer.subscription.deleted.
    logger.warning(
        "stripe invoice.payment_failed org=%s customer=%s amount_due=%s",
        org.id, data.get("customer"), data.get("amount_due"),
    )


_DISPATCH = {
    "checkout.session.completed": _on_checkout_completed,
    "customer.subscription.updated": _on_subscription_updated,
    "customer.subscription.deleted": _on_subscription_deleted,
    "invoice.payment_succeeded": _on_invoice_payment_succeeded,
    "invoice.payment_failed": _on_invoice_payment_failed,
}

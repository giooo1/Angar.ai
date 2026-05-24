"""Resend-backed transactional email (WS4).

Three public functions:

    send_verification_email(user, raw_token, settings)
    send_password_reset_email(user, raw_token, settings)
    send_billing_receipt(user, amount, period_start, period_end, settings)

Every send goes through `_send`, which catches Resend SDK errors and
logs them rather than propagating — an email failure should never
abort the user's signup or a webhook ack. Tests monkeypatch `_send` to
assert call shape without hitting the network.

Templates live in `email_templates/` next to this module as plain
files with `{{ placeholder }}` substitution; no Jinja dep needed.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import resend

from backend.models import User
from backend.settings import Settings

logger = logging.getLogger(__name__)

_TEMPLATE_DIR = Path(__file__).resolve().parent / "email_templates"


def _render(template_name: str, context: dict[str, str]) -> str:
    """Substitute `{{ key }}` placeholders in a template file."""
    text = (_TEMPLATE_DIR / template_name).read_text(encoding="utf-8")
    for key, value in context.items():
        text = text.replace("{{ " + key + " }}", value)
    return text


def _send(
    *,
    to: str,
    subject: str,
    html: str,
    text: str,
    settings: Settings,
) -> None:
    """Resend send + log-on-failure. Does NOT raise.

    No-ops when `resend_api_key` is unset (local dev / tests) so the
    rest of the flow can run unmodified.
    """
    if not settings.resend_api_key:
        logger.info(
            "email: skipped (no RESEND_API_KEY) to=%s subject=%s",
            to, subject,
        )
        return
    try:
        resend.api_key = settings.resend_api_key
        params: dict[str, Any] = {
            "from": settings.email_from,
            "to": to,
            "subject": subject,
            "html": html,
            "text": text,
        }
        resend.Emails.send(params)  # type: ignore[arg-type]
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "email: send failed to=%s subject=%s err=%s",
            to, subject, exc,
        )


def send_verification_email(user: User, raw_token: str, settings: Settings) -> None:
    link = f"{settings.frontend_origin.rstrip('/')}/auth/verify-email?token={raw_token}"
    ctx = {"link": link, "name": user.full_name or user.email}
    html = _render("verify.en.html", ctx)
    text = (
        f"Hi {ctx['name']},\n\n"
        f"Verify your Angar.ai email by clicking this link:\n  {link}\n\n"
        f"The link expires in {settings.email_verify_token_ttl_hours} hours.\n"
    )
    _send(to=user.email, subject="Verify your Angar.ai email", html=html, text=text, settings=settings)


def send_password_reset_email(user: User, raw_token: str, settings: Settings) -> None:
    link = f"{settings.frontend_origin.rstrip('/')}/auth/reset?token={raw_token}"
    ctx = {"link": link, "name": user.full_name or user.email}
    html = _render("reset.en.html", ctx)
    text = (
        f"Hi {ctx['name']},\n\n"
        f"Reset your Angar.ai password by clicking this link:\n  {link}\n\n"
        f"The link expires in {settings.email_reset_token_ttl_hours} hour(s). "
        f"If you didn't ask for this, ignore this email.\n"
    )
    _send(to=user.email, subject="Reset your Angar.ai password", html=html, text=text, settings=settings)


def send_billing_receipt(
    *,
    user: User,
    amount_display: str,
    period_start: datetime,
    period_end: datetime,
    plan: str,
    settings: Settings,
) -> None:
    ctx = {
        "name": user.full_name or user.email,
        "amount": amount_display,
        "plan": plan.capitalize(),
        "period_start": period_start.strftime("%Y-%m-%d"),
        "period_end": period_end.strftime("%Y-%m-%d"),
    }
    html = _render("receipt.en.html", ctx)
    text = (
        f"Hi {ctx['name']},\n\n"
        f"Thanks for your Angar.ai {ctx['plan']} subscription. Your card "
        f"was charged {ctx['amount']} for the period "
        f"{ctx['period_start']} – {ctx['period_end']}.\n"
    )
    _send(to=user.email, subject=f"Receipt — Angar.ai {ctx['plan']}", html=html, text=text, settings=settings)

"""Stripe webhook dispatch tests (Phase 4.5 WS5).

Most tests drive `handle_webhook` directly with fixture payloads — that's
where the plan/quota mutations + idempotency live. One test goes through
the route `/api/v1/webhooks/stripe` to exercise signature verification
and the bad-signature rejection path.

We DO NOT hit real Stripe here. The fixtures are stripped-down versions
of the real Stripe payloads with just the fields our dispatch reads.
"""

from __future__ import annotations

import hmac
import hashlib
import json
import time
from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from backend.auth import get_current_org, get_current_user
from backend.db import get_db
from backend.main import app
from backend.models import Organization, User, WebhookEvent
from backend.routes.extraction import get_settings_dep
from backend.settings import Settings
from backend.stripe_service import handle_webhook


# ---------------------------------------------------------------------------
# Settings + customer-id helpers
# ---------------------------------------------------------------------------

_PRICE_ID_PRO = "price_test_pro"
_PRICE_ID_BUSINESS = "price_test_business"
_WEBHOOK_SECRET = "whsec_test_dummy_secret"
_CUSTOMER_ID = "cus_test_abc"


def _settings(tmp_path) -> Settings:
    return Settings(
        database_url=f"sqlite:///{tmp_path / 'test.db'}",
        storage_dir=tmp_path / "files",
        anthropic_api_key="sk-test",
        jwt_secret="test-jwt-secret",
        resend_api_key="",
        stripe_secret_key="sk_test_dummy",
        stripe_webhook_secret=_WEBHOOK_SECRET,
        stripe_price_id_pro=_PRICE_ID_PRO,
        stripe_price_id_business=_PRICE_ID_BUSINESS,
    )


@pytest.fixture
def linked_org(db_session, test_org):
    """test_org with stripe_customer_id pre-populated so handlers match it."""
    test_org.stripe_customer_id = _CUSTOMER_ID
    db_session.commit()
    db_session.refresh(test_org)
    return test_org


# ---------------------------------------------------------------------------
# Fixture payload builders (mirror real Stripe shape on the keys we read)
# ---------------------------------------------------------------------------


def _evt(event_id: str, event_type: str, data: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": event_id,
        "object": "event",
        "type": event_type,
        "api_version": "2024-04-10",
        "created": int(time.time()),
        "livemode": False,
        "pending_webhooks": 0,
        "request": {"id": None, "idempotency_key": None},
        "data": {"object": data},
    }


def _checkout_completed(plan: str, *, session_id: str = "cs_test_1") -> dict[str, Any]:
    return _evt(
        f"evt_{session_id}",
        "checkout.session.completed",
        {
            "id": session_id,
            "object": "checkout.session",
            "customer": _CUSTOMER_ID,
            "subscription": "sub_test_1",
            "metadata": {"plan": plan},
        },
    )


def _subscription_updated(
    plan: str, *, sub_id: str = "sub_test_1", event_id: str = "evt_sub_upd_1"
) -> dict[str, Any]:
    price_id = _PRICE_ID_PRO if plan == "pro" else _PRICE_ID_BUSINESS
    return _evt(
        event_id,
        "customer.subscription.updated",
        {
            "id": sub_id,
            "object": "subscription",
            "customer": _CUSTOMER_ID,
            "items": {"data": [{"price": {"id": price_id}}]},
        },
    )


def _subscription_deleted() -> dict[str, Any]:
    return _evt(
        "evt_sub_del_1",
        "customer.subscription.deleted",
        {
            "id": "sub_test_1",
            "object": "subscription",
            "customer": _CUSTOMER_ID,
        },
    )


def _invoice_paid(
    *, amount_paid: int = 4900, event_id: str = "evt_inv_paid_1"
) -> dict[str, Any]:
    now = int(time.time())
    return _evt(
        event_id,
        "invoice.payment_succeeded",
        {
            "id": "in_test_1",
            "object": "invoice",
            "customer": _CUSTOMER_ID,
            "amount_paid": amount_paid,
            "currency": "gel",
            "period_start": now - 86400,
            "period_end": now + 86400 * 29,
        },
    )


def _invoice_failed() -> dict[str, Any]:
    return _evt(
        "evt_inv_fail_1",
        "invoice.payment_failed",
        {
            "id": "in_test_2",
            "object": "invoice",
            "customer": _CUSTOMER_ID,
            "amount_due": 4900,
        },
    )


# ---------------------------------------------------------------------------
# Direct-dispatch tests
# ---------------------------------------------------------------------------


class TestCheckoutCompleted:
    def test_upgrades_org_to_pro(self, db_session, linked_org, tmp_path):
        s = _settings(tmp_path)
        handle_webhook(_checkout_completed("pro"), db_session, s)
        db_session.refresh(linked_org)
        assert linked_org.plan == "pro"
        assert linked_org.monthly_extraction_quota == 100
        assert linked_org.monthly_extractions_used == 0
        assert linked_org.stripe_subscription_id == "sub_test_1"

    def test_upgrades_org_to_business(self, db_session, linked_org, tmp_path):
        s = _settings(tmp_path)
        handle_webhook(_checkout_completed("business", session_id="cs_b"), db_session, s)
        db_session.refresh(linked_org)
        assert linked_org.plan == "business"
        assert linked_org.monthly_extraction_quota == 500


class TestSubscriptionUpdated:
    def test_change_to_business_changes_quota(self, db_session, linked_org, tmp_path):
        s = _settings(tmp_path)
        # Start at pro.
        handle_webhook(_checkout_completed("pro"), db_session, s)
        db_session.refresh(linked_org)
        assert linked_org.plan == "pro"

        # Then the user changes to business via the Stripe-hosted portal.
        handle_webhook(_subscription_updated("business"), db_session, s)
        db_session.refresh(linked_org)
        assert linked_org.plan == "business"
        assert linked_org.monthly_extraction_quota == 500


class TestSubscriptionDeleted:
    def test_downgrades_to_free(self, db_session, linked_org, tmp_path):
        s = _settings(tmp_path)
        handle_webhook(_checkout_completed("business"), db_session, s)
        db_session.refresh(linked_org)
        assert linked_org.plan == "business"

        handle_webhook(_subscription_deleted(), db_session, s)
        db_session.refresh(linked_org)
        assert linked_org.plan == "free"
        assert linked_org.monthly_extraction_quota == 50
        assert linked_org.stripe_subscription_id is None


class TestInvoiceEvents:
    def test_invoice_payment_succeeded_sends_receipt(
        self, db_session, linked_org, tmp_path, monkeypatch
    ):
        captured: list[dict[str, Any]] = []

        def _capture(*, to, subject, html, text, settings):
            captured.append({"to": to, "subject": subject})

        monkeypatch.setattr("backend.email._send", _capture)
        s = _settings(tmp_path)
        handle_webhook(_invoice_paid(), db_session, s)
        assert len(captured) == 1
        assert "Receipt" in captured[0]["subject"]

    def test_invoice_payment_failed_does_not_change_plan(
        self, db_session, linked_org, tmp_path
    ):
        s = _settings(tmp_path)
        handle_webhook(_checkout_completed("business"), db_session, s)
        db_session.refresh(linked_org)

        before_plan = linked_org.plan
        before_quota = linked_org.monthly_extraction_quota

        handle_webhook(_invoice_failed(), db_session, s)
        db_session.refresh(linked_org)
        assert linked_org.plan == before_plan
        assert linked_org.monthly_extraction_quota == before_quota


class TestIdempotency:
    def test_double_delivery_does_not_re_apply(self, db_session, linked_org, tmp_path):
        s = _settings(tmp_path)
        handle_webhook(_checkout_completed("pro", session_id="dup"), db_session, s)
        db_session.refresh(linked_org)
        # Manually inflate the counter to detect double-application.
        linked_org.monthly_extractions_used = 17
        db_session.commit()

        # Replay the same event id.
        handle_webhook(_checkout_completed("pro", session_id="dup"), db_session, s)
        db_session.refresh(linked_org)
        # Second delivery short-circuited — counter not reset back to 0.
        assert linked_org.monthly_extractions_used == 17

        # The WebhookEvent row exists exactly once.
        rows = db_session.query(WebhookEvent).filter_by(id="evt_dup").all()
        assert len(rows) == 1


class TestUnhandledAndUnknown:
    def test_unknown_event_type_is_recorded_and_acked(
        self, db_session, linked_org, tmp_path
    ):
        s = _settings(tmp_path)
        evt = _evt("evt_unknown_1", "some.unhandled.type", {"id": "x"})
        # Must not raise.
        handle_webhook(evt, db_session, s)
        rec = db_session.query(WebhookEvent).filter_by(id="evt_unknown_1").one()
        assert rec.type == "some.unhandled.type"

    def test_event_for_unknown_customer_logs_and_acks(
        self, db_session, linked_org, tmp_path
    ):
        s = _settings(tmp_path)
        evt = _checkout_completed("pro", session_id="cs_ghost")
        evt["data"]["object"]["customer"] = "cus_does_not_exist"
        # Must not raise; the org's plan stays untouched.
        before_plan = linked_org.plan
        handle_webhook(evt, db_session, s)
        db_session.refresh(linked_org)
        assert linked_org.plan == before_plan


# ---------------------------------------------------------------------------
# Route-level signature verification
# ---------------------------------------------------------------------------


def _signed_payload(payload_str: str, secret: str = _WEBHOOK_SECRET) -> str:
    """Compute Stripe-style signature header for a test payload."""
    timestamp = str(int(time.time()))
    signed = f"{timestamp}.{payload_str}".encode("utf-8")
    digest = hmac.new(secret.encode("utf-8"), signed, hashlib.sha256).hexdigest()
    return f"t={timestamp},v1={digest}"


@pytest.fixture
def webhook_client(db_session, tmp_path, test_user, test_org):
    settings = _settings(tmp_path)

    def _db_override():
        yield db_session

    app.dependency_overrides[get_db] = _db_override
    app.dependency_overrides[get_settings_dep] = lambda: settings
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_current_org] = lambda: test_org
    from backend.settings import get_settings as _gs
    app.dependency_overrides[_gs] = lambda: settings

    yield TestClient(app), settings

    app.dependency_overrides.clear()


class TestWebhookRoute:
    def test_bad_signature_returns_400(self, webhook_client, linked_org):
        tc, _ = webhook_client
        payload = json.dumps(_checkout_completed("pro", session_id="cs_route_bad"))
        r = tc.post(
            "/api/v1/webhooks/stripe",
            content=payload,
            headers={
                "stripe-signature": "t=1234567890,v1=deadbeef",
                "content-type": "application/json",
            },
        )
        assert r.status_code == 400

    def test_valid_signature_dispatches_and_acks(self, webhook_client, linked_org, db_session):
        tc, _ = webhook_client
        payload = json.dumps(_checkout_completed("pro", session_id="cs_route_ok"))
        r = tc.post(
            "/api/v1/webhooks/stripe",
            content=payload,
            headers={
                "stripe-signature": _signed_payload(payload),
                "content-type": "application/json",
            },
        )
        assert r.status_code == 200, r.text
        db_session.refresh(linked_org)
        assert linked_org.plan == "pro"

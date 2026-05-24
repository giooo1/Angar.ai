"""Tests for the email verification + password reset flow (WS4).

Monkeypatches `backend.email._send` so no network calls fly, and
asserts the call shape + database side-effects.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from backend.auth import get_current_org, get_current_user
from backend.db import get_db
from backend.main import app
from backend.models import EmailToken, User
from backend.rate_limit import limiter
from backend.routes.extraction import get_settings_dep
from backend.settings import Settings


@pytest.fixture
def client(db_session, tmp_path, test_user, test_org, monkeypatch) -> TestClient:
    """Standard test client; no extractor needed for auth tests."""
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'test.db'}",
        storage_dir=tmp_path / "files",
        anthropic_api_key="sk-test-not-real",
        jwt_secret="test-jwt-secret",
        resend_api_key="",  # _send no-ops when empty
        frontend_origin="http://localhost:3000",
    )

    sent: list[dict[str, Any]] = []

    def _capture(*, to, subject, html, text, settings):
        sent.append({"to": to, "subject": subject, "html": html, "text": text})

    monkeypatch.setattr("backend.email._send", _capture)

    def _db_override():
        yield db_session

    app.dependency_overrides[get_db] = _db_override
    app.dependency_overrides[get_settings_dep] = lambda: settings
    # We override these even though most of these tests don't use them,
    # so the existing autouse fixtures stay quiet.
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_current_org] = lambda: test_org

    # Make get_settings (auth router) honor the override too.
    from backend.settings import get_settings as _gs
    app.dependency_overrides[_gs] = lambda: settings

    tc = TestClient(app)
    tc.captured_emails = sent  # type: ignore[attr-defined]
    yield tc

    app.dependency_overrides.clear()


class TestRegistrationSendsVerificationEmail:
    def test_register_creates_pending_verify_token_and_emails_link(
        self, client: TestClient, db_session
    ):
        r = client.post(
            "/api/v1/auth/register",
            json={
                "email": "verifyme@example.com",
                "password": "validpass1",
                "organization_name": "Inc",
            },
        )
        assert r.status_code == 201, r.text
        assert r.json()["user"]["email_verified_at"] is None

        tokens = db_session.query(EmailToken).filter_by(purpose="verify").all()
        assert len(tokens) == 1
        assert tokens[0].used_at is None
        assert tokens[0].expires_at > datetime.now(tz=timezone.utc).replace(tzinfo=None)

        sent = client.captured_emails  # type: ignore[attr-defined]
        assert len(sent) == 1
        assert sent[0]["to"] == "verifyme@example.com"
        assert "Verify" in sent[0]["subject"]
        assert "/auth/verify-email?token=" in sent[0]["html"]


class TestVerifyEmailEndpoint:
    def test_valid_token_marks_user_verified(self, client: TestClient, db_session):
        # Register, grab the raw token from the captured email URL.
        client.post(
            "/api/v1/auth/register",
            json={
                "email": "v@example.com",
                "password": "validpass1",
                "organization_name": "Co",
            },
        )
        link = client.captured_emails[-1]["html"]  # type: ignore[attr-defined]
        token = link.split("token=")[1].split('"')[0]

        r = client.post("/api/v1/auth/verify-email", json={"token": token})
        assert r.status_code == 204

        user = db_session.query(User).filter_by(email="v@example.com").one()
        assert user.email_verified_at is not None

    def test_reused_token_is_rejected(self, client: TestClient, db_session):
        client.post(
            "/api/v1/auth/register",
            json={
                "email": "v2@example.com",
                "password": "validpass1",
                "organization_name": "Co",
            },
        )
        token = (
            client.captured_emails[-1]["html"]  # type: ignore[attr-defined]
            .split("token=")[1]
            .split('"')[0]
        )
        r1 = client.post("/api/v1/auth/verify-email", json={"token": token})
        assert r1.status_code == 204
        r2 = client.post("/api/v1/auth/verify-email", json={"token": token})
        assert r2.status_code == 400
        assert r2.json()["detail"]["error"]["code"] == "INVALID_TOKEN"

    def test_unknown_token_is_rejected(self, client: TestClient):
        r = client.post("/api/v1/auth/verify-email", json={"token": "nope"})
        assert r.status_code == 400
        assert r.json()["detail"]["error"]["code"] == "INVALID_TOKEN"

    def test_expired_token_is_rejected(self, client: TestClient, db_session):
        client.post(
            "/api/v1/auth/register",
            json={
                "email": "v3@example.com",
                "password": "validpass1",
                "organization_name": "Co",
            },
        )
        token = (
            client.captured_emails[-1]["html"]  # type: ignore[attr-defined]
            .split("token=")[1]
            .split('"')[0]
        )
        # Force expiry in the DB.
        row = (
            db_session.query(EmailToken)
            .filter_by(purpose="verify", used_at=None)
            .first()
        )
        row.expires_at = datetime.now(tz=timezone.utc) - timedelta(hours=1)
        db_session.commit()

        r = client.post("/api/v1/auth/verify-email", json={"token": token})
        assert r.status_code == 400
        assert r.json()["detail"]["error"]["code"] == "EXPIRED_TOKEN"


class TestPasswordResetFlow:
    def _register(self, client: TestClient, email: str = "r@example.com") -> None:
        client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "validpass1", "organization_name": "Co"},
        )

    def test_request_reset_emails_link_and_returns_204(
        self, client: TestClient
    ):
        self._register(client)
        client.captured_emails.clear()  # type: ignore[attr-defined]

        r = client.post(
            "/api/v1/auth/request-password-reset",
            json={"email": "r@example.com"},
        )
        assert r.status_code == 204
        sent = client.captured_emails  # type: ignore[attr-defined]
        assert len(sent) == 1
        assert "Reset" in sent[0]["subject"]

    def test_request_reset_for_unknown_email_still_returns_204(
        self, client: TestClient
    ):
        r = client.post(
            "/api/v1/auth/request-password-reset",
            json={"email": "ghost@example.com"},
        )
        assert r.status_code == 204
        # No email sent because no user exists.
        assert client.captured_emails == []  # type: ignore[attr-defined]

    def test_full_reset_round_trip_updates_password_and_logs_in(
        self, client: TestClient, db_session
    ):
        self._register(client, "rt@example.com")
        client.captured_emails.clear()  # type: ignore[attr-defined]

        client.post(
            "/api/v1/auth/request-password-reset",
            json={"email": "rt@example.com"},
        )
        token = (
            client.captured_emails[-1]["html"]  # type: ignore[attr-defined]
            .split("token=")[1]
            .split('"')[0]
        )

        r = client.post(
            "/api/v1/auth/reset-password",
            json={"token": token, "new_password": "newvalidpass1"},
        )
        assert r.status_code == 200, r.text

        # Old password no longer works; new one does.
        bad = client.post(
            "/api/v1/auth/login",
            json={"email": "rt@example.com", "password": "validpass1"},
        )
        assert bad.status_code == 401
        good = client.post(
            "/api/v1/auth/login",
            json={"email": "rt@example.com", "password": "newvalidpass1"},
        )
        assert good.status_code == 200

"""End-to-end tests for the auth flow.

Unlike `test_routes.py`, this file does NOT override `get_current_user`
/ `get_current_org` — it exercises the real JWT cookie path so the auth
module's behavior is actually verified.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt
import pytest
from fastapi.testclient import TestClient

from backend.auth import encode_token
from backend.db import get_db
from backend.main import app
from backend.routes.extraction import get_settings_dep
from backend.settings import Settings


JWT_SECRET = "test-jwt-secret-for-auth-tests"


@pytest.fixture
def auth_client(db_session, tmp_path: Path) -> TestClient:
    """A TestClient with DB / settings overridden but NO auth override.

    Lets the real /auth/register and /auth/login paths run; the session
    cookie is set by the backend and the TestClient carries it forward
    on subsequent requests.
    """
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'test.db'}",
        storage_dir=tmp_path / "files",
        anthropic_api_key="sk-test-not-real",
        jwt_secret=JWT_SECRET,
    )

    def _db_override():
        yield db_session

    app.dependency_overrides[get_db] = _db_override
    app.dependency_overrides[get_settings_dep] = lambda: settings
    # Also override get_settings used inside auth deps (different import path).
    from backend.settings import get_settings as _real_get_settings
    app.dependency_overrides[_real_get_settings] = lambda: settings

    yield TestClient(app)

    app.dependency_overrides.clear()


def _register(client: TestClient, **overrides) -> dict:
    body = {
        "email": "alice@example.com",
        "password": "hunter2pw",
        "full_name": "Alice",
        "organization_name": "Alice's Org",
        **overrides,
    }
    return client.post("/api/v1/auth/register", json=body)


# ---------------------------------------------------------------------------
# register
# ---------------------------------------------------------------------------

class TestRegister:
    def test_happy_path_returns_201_and_sets_cookie(self, auth_client: TestClient) -> None:
        r = _register(auth_client)
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["user"]["email"] == "alice@example.com"
        assert body["user"]["full_name"] == "Alice"
        assert body["organization"]["name"] == "Alice's Org"
        assert "angar_session" in r.cookies

    def test_normalizes_email_to_lowercase(self, auth_client: TestClient) -> None:
        r = _register(auth_client, email="ALICE@Example.COM")
        body = r.json()
        assert body["user"]["email"] == "alice@example.com"

    def test_duplicate_email_returns_409(self, auth_client: TestClient) -> None:
        _register(auth_client)
        r = _register(auth_client, organization_name="Another Org")
        assert r.status_code == 409
        assert r.json()["detail"]["error"]["code"] == "EMAIL_TAKEN"

    def test_weak_password_returns_400(self, auth_client: TestClient) -> None:
        r = _register(auth_client, password="short")
        assert r.status_code == 400
        assert r.json()["detail"]["error"]["code"] == "WEAK_PASSWORD"

    def test_password_without_digits_returns_400(self, auth_client: TestClient) -> None:
        r = _register(auth_client, password="onlyletters")
        assert r.status_code == 400
        assert r.json()["detail"]["error"]["code"] == "WEAK_PASSWORD"

    def test_blank_org_name_returns_400(self, auth_client: TestClient) -> None:
        r = _register(auth_client, organization_name="   ")
        assert r.status_code == 400
        assert r.json()["detail"]["error"]["code"] == "INVALID_ORG_NAME"

    def test_invalid_email_returns_400(self, auth_client: TestClient) -> None:
        r = _register(auth_client, email="not-an-email")
        assert r.status_code == 400
        assert r.json()["detail"]["error"]["code"] == "INVALID_EMAIL"


# ---------------------------------------------------------------------------
# login
# ---------------------------------------------------------------------------

class TestLogin:
    def test_happy_path_returns_200_and_sets_cookie(self, auth_client: TestClient) -> None:
        _register(auth_client)
        r = auth_client.post(
            "/api/v1/auth/login",
            json={"email": "alice@example.com", "password": "hunter2pw"},
        )
        assert r.status_code == 200
        assert r.json()["user"]["email"] == "alice@example.com"
        assert "angar_session" in r.cookies

    def test_wrong_password_returns_401_with_generic_code(
        self, auth_client: TestClient
    ) -> None:
        _register(auth_client)
        r = auth_client.post(
            "/api/v1/auth/login",
            json={"email": "alice@example.com", "password": "WRONG-PW"},
        )
        assert r.status_code == 401
        assert r.json()["detail"]["error"]["code"] == "INVALID_CREDENTIALS"

    def test_unknown_email_returns_401_with_same_code(
        self, auth_client: TestClient
    ) -> None:
        """No user-enumeration: unknown email gives the same code as wrong password."""
        r = auth_client.post(
            "/api/v1/auth/login",
            json={"email": "ghost@example.com", "password": "anything-1"},
        )
        assert r.status_code == 401
        assert r.json()["detail"]["error"]["code"] == "INVALID_CREDENTIALS"


# ---------------------------------------------------------------------------
# logout
# ---------------------------------------------------------------------------

class TestLogout:
    def test_clears_cookie(self, auth_client: TestClient) -> None:
        _register(auth_client)
        r = auth_client.post("/api/v1/auth/logout")
        assert r.status_code == 204
        # Subsequent /me without a cookie returns 401.
        auth_client.cookies.clear()
        r2 = auth_client.get("/api/v1/me")
        assert r2.status_code == 401


# ---------------------------------------------------------------------------
# /me
# ---------------------------------------------------------------------------

class TestMe:
    def test_returns_user_with_cookie(self, auth_client: TestClient) -> None:
        _register(auth_client)
        r = auth_client.get("/api/v1/me")
        assert r.status_code == 200
        body = r.json()
        assert body["user"]["email"] == "alice@example.com"
        assert body["organization"]["name"] == "Alice's Org"

    def test_without_cookie_returns_401(self, auth_client: TestClient) -> None:
        r = auth_client.get("/api/v1/me")
        assert r.status_code == 401
        assert r.json()["detail"]["error"]["code"] == "UNAUTHENTICATED"

    def test_expired_token_returns_401(self, auth_client: TestClient) -> None:
        _register(auth_client)
        # Forge an expired token signed with the real test key.
        now = datetime.now(tz=timezone.utc)
        expired = jwt.encode(
            {
                "sub": "fake",
                "org_id": "fake",
                "iat": int((now - timedelta(hours=2)).timestamp()),
                "exp": int((now - timedelta(hours=1)).timestamp()),
            },
            JWT_SECRET,
            algorithm="HS256",
        )
        auth_client.cookies.set("angar_session", expired)
        r = auth_client.get("/api/v1/me")
        assert r.status_code == 401

    def test_malformed_token_returns_401(self, auth_client: TestClient) -> None:
        auth_client.cookies.set("angar_session", "definitely.not.a.jwt")
        r = auth_client.get("/api/v1/me")
        assert r.status_code == 401

    def test_token_with_unknown_user_returns_401(self, auth_client: TestClient) -> None:
        from backend.settings import Settings

        token = encode_token(
            user_id="ghost-user-id",
            org_id="ghost-org-id",
            settings=Settings(jwt_secret=JWT_SECRET),
        )
        auth_client.cookies.set("angar_session", token)
        r = auth_client.get("/api/v1/me")
        assert r.status_code == 401


# ---------------------------------------------------------------------------
# Gated extraction endpoint actually rejects unauthenticated callers
# ---------------------------------------------------------------------------

class TestExtractionGating:
    def test_list_extractions_without_auth_returns_401(
        self, auth_client: TestClient
    ) -> None:
        r = auth_client.get("/api/v1/extractions")
        assert r.status_code == 401
        assert r.json()["detail"]["error"]["code"] == "UNAUTHENTICATED"

    def test_list_extractions_after_register_returns_200(
        self, auth_client: TestClient
    ) -> None:
        _register(auth_client)
        r = auth_client.get("/api/v1/extractions")
        assert r.status_code == 200
        assert r.json()["items"] == []  # fresh org, no uploads


class TestUpdateProfile:
    def test_updates_name_and_locale(self, auth_client: TestClient) -> None:
        _register(auth_client)
        r = auth_client.patch("/api/v1/me", json={"full_name": "Alice Smith", "locale": "ka"})
        assert r.status_code == 200, r.text
        user = r.json()["user"]
        assert user["full_name"] == "Alice Smith"
        assert user["locale"] == "ka"
        # Persisted: a fresh /me reflects it.
        assert auth_client.get("/api/v1/me").json()["user"]["locale"] == "ka"

    def test_partial_update_leaves_other_fields(self, auth_client: TestClient) -> None:
        _register(auth_client)
        auth_client.patch("/api/v1/me", json={"locale": "ka"})
        r = auth_client.patch("/api/v1/me", json={"full_name": "Just Name"})
        user = r.json()["user"]
        assert user["full_name"] == "Just Name"
        assert user["locale"] == "ka"  # untouched

    def test_invalid_locale_returns_400(self, auth_client: TestClient) -> None:
        _register(auth_client)
        r = auth_client.patch("/api/v1/me", json={"locale": "fr"})
        assert r.status_code == 400
        assert r.json()["detail"]["error"]["code"] == "INVALID_LOCALE"

    def test_requires_auth(self, auth_client: TestClient) -> None:
        r = auth_client.patch("/api/v1/me", json={"full_name": "x"})
        assert r.status_code == 401


class TestChangePassword:
    def _login(self, client: TestClient, password: str):
        return client.post(
            "/api/v1/auth/login",
            json={"email": "alice@example.com", "password": password},
        )

    def test_change_then_old_fails_new_works(self, auth_client: TestClient) -> None:
        _register(auth_client)
        r = auth_client.post(
            "/api/v1/auth/change-password",
            json={"current_password": "hunter2pw", "new_password": "brandnewpw9"},
        )
        assert r.status_code == 204, r.text
        auth_client.post("/api/v1/auth/logout")
        assert self._login(auth_client, "hunter2pw").status_code == 401
        assert self._login(auth_client, "brandnewpw9").status_code == 200

    def test_wrong_current_returns_400(self, auth_client: TestClient) -> None:
        _register(auth_client)
        r = auth_client.post(
            "/api/v1/auth/change-password",
            json={"current_password": "wrongpass", "new_password": "brandnewpw9"},
        )
        assert r.status_code == 400
        assert r.json()["detail"]["error"]["code"] == "WRONG_PASSWORD"

    def test_short_new_returns_400(self, auth_client: TestClient) -> None:
        _register(auth_client)
        r = auth_client.post(
            "/api/v1/auth/change-password",
            json={"current_password": "hunter2pw", "new_password": "short"},
        )
        assert r.status_code == 400

    def test_requires_auth(self, auth_client: TestClient) -> None:
        r = auth_client.post(
            "/api/v1/auth/change-password",
            json={"current_password": "x", "new_password": "brandnewpw9"},
        )
        assert r.status_code == 401


class TestGoogleOAuth:
    """Callback-side coverage with the Google HTTP calls monkeypatched.

    The two `_google_*` helpers are stubbed so no real network call is made;
    state-cookie / provisioning / linking logic is exercised end to end.
    """

    def _stub_google(self, monkeypatch, *, email: str, verified: bool = True, name: str | None = "Some One"):
        monkeypatch.setattr(
            "backend.routes.auth._google_exchange_code",
            lambda code, settings: {"access_token": "stub-access-token"},
        )
        monkeypatch.setattr(
            "backend.routes.auth._google_userinfo",
            lambda access_token: {"email": email, "email_verified": verified, "name": name},
        )

    def test_unconfigured_start_redirects_with_error(self, auth_client: TestClient) -> None:
        # The test settings have no google_client_id.
        r = auth_client.get("/api/v1/auth/google/start", follow_redirects=False)
        assert r.status_code == 302
        assert r.headers["location"].endswith("/login?error=google_unconfigured")

    def test_new_email_provisions_account_and_signs_in(
        self, auth_client: TestClient, monkeypatch
    ) -> None:
        self._stub_google(monkeypatch, email="newperson@example.com", name="New Person")
        auth_client.cookies.set("g_oauth_state", "state123")
        r = auth_client.get(
            "/api/v1/auth/google/callback?code=abc&state=state123",
            follow_redirects=False,
        )
        assert r.status_code == 302, r.text
        assert r.headers["location"].endswith("/upload")
        assert "angar_session" in r.cookies
        # The freshly-set session works.
        me = auth_client.get("/api/v1/me")
        assert me.status_code == 200
        body = me.json()
        assert body["user"]["email"] == "newperson@example.com"
        # Auto-provisioned org named off the Google display name.
        assert "New" in body["organization"]["name"]

    def test_existing_email_links_without_duplicate_org(
        self, auth_client: TestClient, db_session, monkeypatch
    ) -> None:
        from sqlalchemy import select as _select
        from backend.models import OrganizationMember, User

        _register(auth_client)  # alice@example.com + her org
        auth_client.cookies.clear()  # drop the register session; sign in via Google

        self._stub_google(monkeypatch, email="alice@example.com", name="Alice")
        auth_client.cookies.set("g_oauth_state", "st")
        r = auth_client.get(
            "/api/v1/auth/google/callback?code=abc&state=st",
            follow_redirects=False,
        )
        assert r.status_code == 302
        assert "angar_session" in r.cookies
        assert auth_client.get("/api/v1/me").json()["user"]["email"] == "alice@example.com"

        user = db_session.execute(
            _select(User).where(User.email == "alice@example.com")
        ).scalar_one()
        memberships = db_session.execute(
            _select(OrganizationMember).where(OrganizationMember.user_id == user.id)
        ).scalars().all()
        assert len(memberships) == 1  # linked, not a second org

    def test_state_mismatch_is_rejected(
        self, auth_client: TestClient, monkeypatch
    ) -> None:
        self._stub_google(monkeypatch, email="x@example.com")
        auth_client.cookies.set("g_oauth_state", "real-state")
        r = auth_client.get(
            "/api/v1/auth/google/callback?code=abc&state=forged",
            follow_redirects=False,
        )
        assert r.status_code == 302
        assert r.headers["location"].endswith("/login?error=google_state")

    def test_unverified_google_email_is_rejected(
        self, auth_client: TestClient, monkeypatch
    ) -> None:
        self._stub_google(monkeypatch, email="unverified@example.com", verified=False)
        auth_client.cookies.set("g_oauth_state", "s")
        r = auth_client.get(
            "/api/v1/auth/google/callback?code=abc&state=s",
            follow_redirects=False,
        )
        assert r.status_code == 302
        assert r.headers["location"].endswith("/login?error=google_unverified")

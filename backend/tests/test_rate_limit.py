"""Tests for the slowapi rate limiter (WS3).

The autouse `_disable_rate_limiter` in conftest keeps every other test
unconstrained. These tests opt back in by enabling the limiter inside
their own scope.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from angar_extraction.extractor import ExtractionResult
from angar_schema.canonical import (
    CanonicalInvoice,
    Currency,
    DocumentType,
    ExtractionMetadata,
)
from backend.auth import get_current_org, get_current_user
from backend.db import get_db
from backend.main import app
from backend.rate_limit import limiter
from backend.routes.extraction import (
    get_extractor_dep,
    get_settings_dep,
    get_storage,
)
from backend.settings import Settings


@pytest.fixture
def enable_limiter():
    """Re-enable the limiter for one test, then reset + disable again."""
    limiter.reset()
    limiter.enabled = True
    try:
        yield
    finally:
        limiter.enabled = False
        limiter.reset()


@pytest.fixture
def client(db_session, tmp_storage, tmp_path, test_user, test_org) -> TestClient:
    """Standard test client; mirrors test_routes.py."""
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'test.db'}",
        storage_dir=tmp_path / "files",
        anthropic_api_key="sk-test-not-real",
        jwt_secret="test-jwt-secret",
    )

    def _valid_canonical() -> CanonicalInvoice:
        return CanonicalInvoice(
            accepted=True,
            document_type=DocumentType.REGULAR_INVOICE,
            document_number="RL-1",
            document_currency=Currency.GEL,
            extraction=ExtractionMetadata(
                source_filename="x.pdf",
                source_pdf_sha256="abc",
                extracted_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
                model_version="claude-sonnet-4-6",
                prompt_version="v3",
            ),
        )

    mock_extractor = MagicMock()
    mock_extractor.model = "claude-sonnet-4-6"
    mock_extractor.prompt_version = "v3"
    mock_extractor.extract.return_value = ExtractionResult(
        canonical=_valid_canonical(),
        raw_response="{}",
        input_tokens=10,
        cached_input_tokens=0,
        output_tokens=10,
        processing_time_ms=10,
        parse_error=None,
    )

    def _db_override():
        yield db_session

    app.dependency_overrides[get_db] = _db_override
    app.dependency_overrides[get_storage] = lambda: tmp_storage
    app.dependency_overrides[get_extractor_dep] = lambda: mock_extractor
    app.dependency_overrides[get_settings_dep] = lambda: settings
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_current_org] = lambda: test_org

    yield TestClient(app)

    app.dependency_overrides.clear()


class TestAuthLoginRateLimit:
    def test_sixth_login_in_a_minute_returns_429(
        self, enable_limiter, client: TestClient
    ) -> None:
        body = {"email": "nobody@example.com", "password": "wrongpass1"}
        # First 5 should be allowed (401 — wrong credentials).
        for i in range(5):
            r = client.post("/api/v1/auth/login", json=body)
            assert r.status_code == 401, f"call #{i + 1}: {r.text}"
        # 6th hits the limit.
        r = client.post("/api/v1/auth/login", json=body)
        assert r.status_code == 429
        assert r.json()["detail"]["error"]["code"] == "RATE_LIMITED"


class TestRegisterRateLimit:
    def test_fourth_register_in_an_hour_returns_429(
        self, enable_limiter, client: TestClient
    ) -> None:
        # 3/hour limit. Each call uses a fresh email to avoid 409 collisions.
        for i in range(3):
            r = client.post(
                "/api/v1/auth/register",
                json={
                    "email": f"r{i}@example.com",
                    "password": "validpass1",
                    "organization_name": "Co",
                },
            )
            assert r.status_code == 201, f"call #{i + 1}: {r.text}"
        # 4th hits the limit.
        r = client.post(
            "/api/v1/auth/register",
            json={
                "email": "r3@example.com",
                "password": "validpass1",
                "organization_name": "Co",
            },
        )
        assert r.status_code == 429
        assert r.json()["detail"]["error"]["code"] == "RATE_LIMITED"

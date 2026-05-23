"""Tests for the quota gate (Phase 4 step 6).

Covers:
- Counter increments on a successful new upload.
- 429 when used == quota; not blocked at used == quota - 1.
- Dedup uploads do NOT consume quota.
- Re-extract counts (calls the model).
- reset_if_due rolls the window forward once the reset_at has passed.
- /me reflects the latest counter.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
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
from backend.models import Organization
from backend.quota import reset_if_due
from backend.routes.extraction import (
    get_extractor_dep,
    get_settings_dep,
    get_storage,
)
from backend.settings import Settings


def _valid_canonical() -> CanonicalInvoice:
    return CanonicalInvoice(
        accepted=True,
        document_type=DocumentType.REGULAR_INVOICE,
        document_number="Q-1",
        document_currency=Currency.GEL,
        extraction=ExtractionMetadata(
            source_filename="x.pdf",
            source_pdf_sha256="abc",
            extracted_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            model_version="claude-sonnet-4-6",
            prompt_version="v3",
        ),
    )


def _success() -> ExtractionResult:
    return ExtractionResult(
        canonical=_valid_canonical(),
        raw_response="{}",
        input_tokens=100,
        cached_input_tokens=80,
        output_tokens=200,
        processing_time_ms=1234,
        parse_error=None,
    )


@pytest.fixture
def client(db_session, tmp_storage, tmp_path, test_user, test_org) -> TestClient:
    """TestClient with auth + extractor mocked so quota is the only thing under test."""
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'test.db'}",
        storage_dir=tmp_path / "files",
        anthropic_api_key="sk-test-not-real",
        jwt_secret="test-jwt-secret",
    )
    mock_extractor = MagicMock()
    mock_extractor.model = "claude-sonnet-4-6"
    mock_extractor.prompt_version = "v3"
    mock_extractor.extract.return_value = _success()

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


def _set_used(db_session, org: Organization, used: int) -> None:
    org.monthly_extractions_used = used
    db_session.commit()
    db_session.refresh(org)


# ---------------------------------------------------------------------------
# Upload path
# ---------------------------------------------------------------------------


class TestUploadQuota:
    def test_first_upload_increments_counter(
        self, client: TestClient, db_session, test_org
    ) -> None:
        r = client.post(
            "/api/v1/documents",
            files={"file": ("a.pdf", b"%PDF-1.4 a", "application/pdf")},
        )
        assert r.status_code == 202, r.text
        db_session.refresh(test_org)
        assert test_org.monthly_extractions_used == 1

    def test_upload_at_quota_minus_one_still_succeeds(
        self, client: TestClient, db_session, test_org
    ) -> None:
        _set_used(db_session, test_org, 49)
        r = client.post(
            "/api/v1/documents",
            files={"file": ("b.pdf", b"%PDF-1.4 b", "application/pdf")},
        )
        assert r.status_code == 202
        db_session.refresh(test_org)
        assert test_org.monthly_extractions_used == 50

    def test_upload_at_quota_returns_429(
        self, client: TestClient, db_session, test_org
    ) -> None:
        _set_used(db_session, test_org, 50)
        r = client.post(
            "/api/v1/documents",
            files={"file": ("c.pdf", b"%PDF-1.4 c", "application/pdf")},
        )
        assert r.status_code == 429
        body = r.json()
        assert body["detail"]["code"] == "QUOTA_EXHAUSTED"
        assert body["detail"]["quota"] == 50
        assert body["detail"]["used"] == 50
        assert "resets_at" in body["detail"]
        db_session.refresh(test_org)
        assert test_org.monthly_extractions_used == 50  # not incremented past cap

    def test_duplicate_upload_does_not_consume_quota(
        self, client: TestClient, db_session, test_org
    ) -> None:
        _set_used(db_session, test_org, 10)
        same_bytes = b"%PDF-1.4 dedup"
        first = client.post(
            "/api/v1/documents",
            files={"file": ("dup1.pdf", same_bytes, "application/pdf")},
        )
        assert first.status_code == 202
        db_session.refresh(test_org)
        assert test_org.monthly_extractions_used == 11

        second = client.post(
            "/api/v1/documents",
            files={"file": ("dup2.pdf", same_bytes, "application/pdf")},
        )
        assert second.status_code == 202
        db_session.refresh(test_org)
        # second upload dedup'd onto the first doc — no model call, no quota cost.
        assert test_org.monthly_extractions_used == 11


# ---------------------------------------------------------------------------
# Re-extract path
# ---------------------------------------------------------------------------


class TestReextractQuota:
    def test_reextract_consumes_quota(
        self, client: TestClient, db_session, test_org
    ) -> None:
        _set_used(db_session, test_org, 0)
        upload = client.post(
            "/api/v1/documents",
            files={"file": ("re.pdf", b"%PDF re-1", "application/pdf")},
        ).json()
        db_session.refresh(test_org)
        assert test_org.monthly_extractions_used == 1

        r = client.post(f"/api/v1/documents/{upload['document_id']}/extract")
        assert r.status_code == 202, r.text
        db_session.refresh(test_org)
        assert test_org.monthly_extractions_used == 2

    def test_reextract_at_quota_returns_429(
        self, client: TestClient, db_session, test_org
    ) -> None:
        # First create a doc with quota plenty.
        _set_used(db_session, test_org, 0)
        upload = client.post(
            "/api/v1/documents",
            files={"file": ("re2.pdf", b"%PDF re-2", "application/pdf")},
        ).json()
        # Drive the counter to the cap and try to re-extract.
        _set_used(db_session, test_org, 50)
        r = client.post(f"/api/v1/documents/{upload['document_id']}/extract")
        assert r.status_code == 429
        assert r.json()["detail"]["code"] == "QUOTA_EXHAUSTED"


# ---------------------------------------------------------------------------
# Rolling window
# ---------------------------------------------------------------------------


class TestResetIfDue:
    def test_resets_when_reset_at_is_in_the_past(
        self, db_session, test_org
    ) -> None:
        test_org.monthly_extractions_used = 47
        test_org.quota_reset_at = datetime.now(tz=timezone.utc) - timedelta(hours=1)
        db_session.commit()

        reset_if_due(test_org)
        db_session.commit()
        db_session.refresh(test_org)

        assert test_org.monthly_extractions_used == 0
        future = test_org.quota_reset_at
        if future.tzinfo is None:
            future = future.replace(tzinfo=timezone.utc)
        assert future > datetime.now(tz=timezone.utc)

    def test_noop_when_reset_at_is_in_the_future(
        self, db_session, test_org
    ) -> None:
        test_org.monthly_extractions_used = 7
        old_reset = datetime.now(tz=timezone.utc) + timedelta(days=10)
        test_org.quota_reset_at = old_reset
        db_session.commit()

        reset_if_due(test_org)

        assert test_org.monthly_extractions_used == 7
        stored = test_org.quota_reset_at
        if stored.tzinfo is None:
            stored = stored.replace(tzinfo=timezone.utc)
        assert stored == old_reset

    def test_upload_after_expiry_rolls_window_forward(
        self, client: TestClient, db_session, test_org
    ) -> None:
        # Cap reached, but the reset window is already in the past — next
        # upload should reset the counter to 0 and then increment to 1.
        test_org.monthly_extractions_used = 50
        test_org.quota_reset_at = datetime.now(tz=timezone.utc) - timedelta(seconds=1)
        db_session.commit()

        r = client.post(
            "/api/v1/documents",
            files={"file": ("rolled.pdf", b"%PDF rolled", "application/pdf")},
        )
        assert r.status_code == 202, r.text
        db_session.refresh(test_org)
        assert test_org.monthly_extractions_used == 1


# ---------------------------------------------------------------------------
# /me reflects live counter
# ---------------------------------------------------------------------------


class TestMeReportsQuota:
    def test_me_returns_updated_used_after_uploads(
        self, client: TestClient
    ) -> None:
        client.post(
            "/api/v1/documents",
            files={"file": ("m1.pdf", b"%PDF m-1", "application/pdf")},
        )
        client.post(
            "/api/v1/documents",
            files={"file": ("m2.pdf", b"%PDF m-2", "application/pdf")},
        )
        r = client.get("/api/v1/me")
        assert r.status_code == 200
        org = r.json()["organization"]
        assert org["monthly_extraction_quota"] == 50
        assert org["monthly_extractions_used"] == 2

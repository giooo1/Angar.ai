"""End-to-end route tests using FastAPI TestClient.

Every dependency is overridden so no real Anthropic calls, no real
filesystem outside tmp_path, no real DB outside tmp_path.
"""

from __future__ import annotations

from datetime import datetime, timezone
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
from backend.db import get_db
from backend.main import app
from backend.routes.extraction import (
    get_extractor_dep,
    get_settings_dep,
    get_storage,
)
from backend.settings import Settings


def _valid_canonical(document_number: str = "TEST-1") -> CanonicalInvoice:
    return CanonicalInvoice(
        accepted=True,
        document_type=DocumentType.REGULAR_INVOICE,
        document_number=document_number,
        document_currency=Currency.GEL,
        extraction=ExtractionMetadata(
            source_filename="x.pdf",
            source_pdf_sha256="abc",
            extracted_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            model_version="claude-sonnet-4-6",
            prompt_version="v3",
        ),
    )


def _success(doc_num: str = "TEST-1") -> ExtractionResult:
    return ExtractionResult(
        canonical=_valid_canonical(doc_num),
        raw_response="{}",
        input_tokens=100,
        cached_input_tokens=80,
        output_tokens=200,
        processing_time_ms=1234,
        parse_error=None,
    )


@pytest.fixture
def client(db_session, tmp_storage, tmp_path) -> TestClient:
    """A TestClient with every external dependency overridden."""
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'test.db'}",
        storage_dir=tmp_path / "files",
        anthropic_api_key="sk-test-not-real",
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

    yield TestClient(app)

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Healthcheck
# ---------------------------------------------------------------------------

class TestHealthcheck:
    def test_healthz_returns_ok(self, client: TestClient) -> None:
        r = client.get("/healthz")
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# POST /api/v1/documents
# ---------------------------------------------------------------------------

class TestUploadDocument:
    def test_upload_returns_202_with_completed_status(self, client: TestClient) -> None:
        r = client.post(
            "/api/v1/documents",
            files={"file": ("invoice.pdf", b"%PDF-1.4 fake content", "application/pdf")},
        )
        assert r.status_code == 202, r.text
        body = r.json()
        assert "document_id" in body
        assert "extraction_id" in body
        assert body["status"] == "completed"

    def test_dedup_returns_same_ids_on_second_upload(self, client: TestClient) -> None:
        first = client.post(
            "/api/v1/documents",
            files={"file": ("a.pdf", b"same-bytes", "application/pdf")},
        ).json()
        second = client.post(
            "/api/v1/documents",
            files={"file": ("a-again.pdf", b"same-bytes", "application/pdf")},
        ).json()
        assert first["document_id"] == second["document_id"]
        assert first["extraction_id"] == second["extraction_id"]

    def test_rejects_wrong_mime_type(self, client: TestClient) -> None:
        r = client.post(
            "/api/v1/documents",
            files={"file": ("notes.txt", b"not a pdf", "text/plain")},
        )
        assert r.status_code == 415
        assert r.json()["detail"]["error"]["code"] == "INVALID_FILE_TYPE"

    def test_rejects_oversize_file(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        # Tweak settings on the fly: override returns a tiny limit.
        small_settings = Settings(
            database_url=f"sqlite:///{tmp_path / 'test.db'}",
            storage_dir=tmp_path / "files",
            anthropic_api_key="sk-test",
            max_upload_bytes=10,
        )
        app.dependency_overrides[get_settings_dep] = lambda: small_settings
        r = client.post(
            "/api/v1/documents",
            files={"file": ("big.pdf", b"x" * 100, "application/pdf")},
        )
        assert r.status_code == 413
        assert r.json()["detail"]["error"]["code"] == "FILE_TOO_LARGE"


# ---------------------------------------------------------------------------
# GET /api/v1/extractions/{id}
# ---------------------------------------------------------------------------

class TestGetExtraction:
    def test_returns_canonical_after_upload(self, client: TestClient) -> None:
        upload = client.post(
            "/api/v1/documents",
            files={"file": ("x.pdf", b"%PDF body", "application/pdf")},
        ).json()
        r = client.get(f"/api/v1/extractions/{upload['extraction_id']}")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "completed"
        assert body["canonical_data"]["document_number"] == "TEST-1"
        assert body["prompt_version"] == "v3"
        assert body["model_version"] == "claude-sonnet-4-6"

    def test_404_for_unknown_id(self, client: TestClient) -> None:
        r = client.get("/api/v1/extractions/does-not-exist")
        assert r.status_code == 404
        assert r.json()["detail"]["error"]["code"] == "EXTRACTION_NOT_FOUND"


# ---------------------------------------------------------------------------
# POST /api/v1/documents/{id}/extract — re-extract
# ---------------------------------------------------------------------------

class TestReextract:
    def test_creates_new_extraction_row(self, client: TestClient) -> None:
        upload = client.post(
            "/api/v1/documents",
            files={"file": ("x.pdf", b"%PDF body", "application/pdf")},
        ).json()
        doc_id = upload["document_id"]
        first_ex = upload["extraction_id"]

        r = client.post(f"/api/v1/documents/{doc_id}/extract")
        assert r.status_code == 202, r.text
        body = r.json()
        assert body["document_id"] == doc_id
        assert body["extraction_id"] != first_ex
        assert body["status"] == "completed"

    def test_404_for_unknown_document(self, client: TestClient) -> None:
        r = client.post("/api/v1/documents/nope/extract")
        assert r.status_code == 404
        assert r.json()["detail"]["error"]["code"] == "DOCUMENT_NOT_FOUND"

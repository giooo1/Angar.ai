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
from backend.auth import get_current_org, get_current_user
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
def client(db_session, tmp_storage, tmp_path, test_user, test_org) -> TestClient:
    """A TestClient with every external dependency overridden.

    Auth is stubbed: get_current_user / get_current_org return the
    fixture user/org so route tests don't need to call /auth/login.
    """
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


# ---------------------------------------------------------------------------
# GET /api/v1/documents/{id}/file — original PDF streaming
# ---------------------------------------------------------------------------

class TestGetDocumentFile:
    def test_returns_pdf_bytes_inline(self, client: TestClient) -> None:
        pdf_bytes = b"%PDF-1.4 fake content here"
        upload = client.post(
            "/api/v1/documents",
            files={"file": ("source.pdf", pdf_bytes, "application/pdf")},
        ).json()

        r = client.get(f"/api/v1/documents/{upload['document_id']}/file")
        assert r.status_code == 200
        assert r.content == pdf_bytes
        assert r.headers["content-type"].startswith("application/pdf")
        assert "inline" in r.headers["content-disposition"]
        assert "source.pdf" in r.headers["content-disposition"]

    def test_404_for_unknown_document(self, client: TestClient) -> None:
        r = client.get("/api/v1/documents/does-not-exist/file")
        assert r.status_code == 404
        assert r.json()["detail"]["error"]["code"] == "DOCUMENT_NOT_FOUND"

    def test_404_for_soft_deleted_document(
        self, client: TestClient, db_session
    ) -> None:
        from datetime import datetime, timezone

        from backend.models import Document

        upload = client.post(
            "/api/v1/documents",
            files={"file": ("x.pdf", b"%PDF body", "application/pdf")},
        ).json()

        doc = db_session.get(Document, upload["document_id"])
        doc.deleted_at = datetime.now(tz=timezone.utc)
        db_session.commit()

        r = client.get(f"/api/v1/documents/{upload['document_id']}/file")
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# GET /api/v1/extractions — paginated list
# ---------------------------------------------------------------------------

class TestListExtractions:
    def _seed_uploads(self, client: TestClient, count: int) -> list[str]:
        ids: list[str] = []
        for i in range(count):
            r = client.post(
                "/api/v1/documents",
                files={
                    "file": (
                        f"doc-{i}.pdf",
                        f"%PDF unique content {i}".encode(),
                        "application/pdf",
                    )
                },
            )
            ids.append(r.json()["extraction_id"])
        return ids

    def test_empty_when_no_extractions(self, client: TestClient) -> None:
        r = client.get("/api/v1/extractions")
        assert r.status_code == 200
        body = r.json()
        assert body["items"] == []
        assert body["total"] == 0
        assert body["page"] == 1
        assert body["page_size"] == 25

    def test_returns_items_newest_first(self, client: TestClient) -> None:
        ids = self._seed_uploads(client, count=3)
        r = client.get("/api/v1/extractions")
        body = r.json()
        assert body["total"] == 3
        # The most recently created extraction is item 0.
        returned_ids = [item["extraction_id"] for item in body["items"]]
        assert returned_ids == list(reversed(ids))

    def test_pagination(self, client: TestClient) -> None:
        self._seed_uploads(client, count=5)
        r = client.get("/api/v1/extractions?page=1&page_size=2")
        body = r.json()
        assert body["total"] == 5
        assert len(body["items"]) == 2
        assert body["page"] == 1
        assert body["page_size"] == 2

        r2 = client.get("/api/v1/extractions?page=3&page_size=2")
        body2 = r2.json()
        assert len(body2["items"]) == 1  # last page has 1 item
        assert body2["page"] == 3

    def test_filters_by_org(
        self, client: TestClient, db_session, tmp_path: Path
    ) -> None:
        """Extractions from a different org must not leak into the list."""
        from backend.models import Document, Extraction
        import uuid

        self._seed_uploads(client, count=2)

        # Insert one document + extraction under a different org directly.
        other_doc = Document(
            id=str(uuid.uuid4()),
            organization_id="other-org",
            uploaded_by_user_id="someone-else",
            original_filename="other.pdf",
            file_sha256="dead",
            file_size_bytes=10,
            file_mime_type="application/pdf",
            storage_path="other-org/dead.pdf",
        )
        db_session.add(other_doc)
        db_session.flush()
        other_ext = Extraction(
            id=str(uuid.uuid4()),
            document_id=other_doc.id,
            status="completed",
            prompt_version="v3",
            model_version="claude-sonnet-4-6",
        )
        db_session.add(other_ext)
        db_session.commit()

        r = client.get("/api/v1/extractions")
        body = r.json()
        assert body["total"] == 2
        returned_ids = {item["extraction_id"] for item in body["items"]}
        assert other_ext.id not in returned_ids

    def test_invalid_page_returns_422(self, client: TestClient) -> None:
        r = client.get("/api/v1/extractions?page=0")
        assert r.status_code == 422  # FastAPI validation: page must be >= 1

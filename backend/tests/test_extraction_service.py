"""Unit tests for backend.extraction_service.

No real Anthropic calls — every test injects a MagicMock Extractor whose
`.extract(path)` returns a hand-built ExtractionResult.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from angar_extraction.extractor import ExtractionResult
from angar_schema.canonical import (
    CanonicalInvoice,
    Currency,
    DocumentType,
    ExtractionMetadata,
)
from backend.extraction_service import (
    ExtractionServiceError,
    create_reextract,
    run_extraction,
    store_uploaded_file,
)
from backend.models import Document, Extraction
from backend.settings import Settings


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _settings(tmp_path: Path) -> Settings:
    """A Settings instance pointing at tmp_path for isolation."""
    return Settings(
        database_url=f"sqlite:///{tmp_path / 'test.db'}",
        storage_dir=tmp_path / "files",
        anthropic_api_key="sk-test-not-real",
    )


def _valid_canonical() -> CanonicalInvoice:
    return CanonicalInvoice(
        accepted=True,
        document_type=DocumentType.REGULAR_INVOICE,
        document_number="TEST-1",
        document_currency=Currency.GEL,
        extraction=ExtractionMetadata(
            source_filename="x.pdf",
            source_pdf_sha256="abc",
            extracted_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            model_version="claude-sonnet-4-6",
            prompt_version="v3",
        ),
    )


def _success_result() -> ExtractionResult:
    return ExtractionResult(
        canonical=_valid_canonical(),
        raw_response="{}",
        input_tokens=100,
        cached_input_tokens=50,
        output_tokens=200,
        processing_time_ms=1234,
        parse_error=None,
    )


def _parse_fail_result() -> ExtractionResult:
    return ExtractionResult(
        canonical=None,
        raw_response="bad",
        input_tokens=100,
        cached_input_tokens=0,
        output_tokens=10,
        processing_time_ms=500,
        parse_error="json decode at line 5",
    )


def _mock_extractor(result: ExtractionResult) -> MagicMock:
    e = MagicMock()
    e.model = "claude-sonnet-4-6"
    e.prompt_version = "v3"
    e.extract.return_value = result
    return e


# ---------------------------------------------------------------------------
# store_uploaded_file
# ---------------------------------------------------------------------------

class TestStoreUploadedFile:
    def test_creates_doc_and_extraction(self, db_session, tmp_storage, tmp_path) -> None:
        s = _settings(tmp_path)
        doc, ex, is_new = store_uploaded_file(
            content=b"hello",
            filename="invoice.pdf",
            mime="application/pdf",
            storage=tmp_storage,
            db=db_session,
            settings=s,
        )
        assert is_new is True
        assert doc.original_filename == "invoice.pdf"
        assert doc.file_size_bytes == 5
        assert doc.organization_id == "demo-org"
        assert tmp_storage.exists(doc.storage_path)
        assert ex.status == "pending"
        assert ex.document_id == doc.id

    def test_dedupes_same_content_same_org(self, db_session, tmp_storage, tmp_path) -> None:
        s = _settings(tmp_path)
        d1, e1, new1 = store_uploaded_file(
            content=b"same", filename="a.pdf", mime="application/pdf",
            storage=tmp_storage, db=db_session, settings=s,
        )
        d2, e2, new2 = store_uploaded_file(
            content=b"same", filename="a-dupe.pdf", mime="application/pdf",
            storage=tmp_storage, db=db_session, settings=s,
        )
        assert new1 is True
        assert new2 is False
        assert d1.id == d2.id
        assert e1.id == e2.id

    def test_same_content_different_orgs_creates_separate_docs(
        self, db_session, tmp_storage, tmp_path
    ) -> None:
        s = _settings(tmp_path)
        d1, _, new1 = store_uploaded_file(
            content=b"x", filename="a.pdf", mime="application/pdf",
            storage=tmp_storage, db=db_session, settings=s,
            org_id="org-a",
        )
        d2, _, new2 = store_uploaded_file(
            content=b"x", filename="a.pdf", mime="application/pdf",
            storage=tmp_storage, db=db_session, settings=s,
            org_id="org-b",
        )
        assert new1 is True
        assert new2 is True
        assert d1.id != d2.id
        assert d1.organization_id == "org-a"
        assert d2.organization_id == "org-b"

    def test_rejects_oversize_file(self, db_session, tmp_storage, tmp_path) -> None:
        s = _settings(tmp_path)
        s.max_upload_bytes = 4  # type: ignore[misc]
        with pytest.raises(ExtractionServiceError, match="max upload size"):
            store_uploaded_file(
                content=b"too long", filename="x.pdf", mime="application/pdf",
                storage=tmp_storage, db=db_session, settings=s,
            )

    def test_rejects_disallowed_mime(self, db_session, tmp_storage, tmp_path) -> None:
        s = _settings(tmp_path)
        with pytest.raises(ExtractionServiceError, match="mime type"):
            store_uploaded_file(
                content=b"x", filename="x.txt", mime="text/plain",
                storage=tmp_storage, db=db_session, settings=s,
            )


# ---------------------------------------------------------------------------
# run_extraction
# ---------------------------------------------------------------------------

class TestRunExtraction:
    def test_success_populates_canonical(self, db_session, tmp_storage, tmp_path) -> None:
        s = _settings(tmp_path)
        doc, ex, _ = store_uploaded_file(
            content=b"pdf-bytes", filename="x.pdf", mime="application/pdf",
            storage=tmp_storage, db=db_session, settings=s,
        )
        extractor = _mock_extractor(_success_result())
        result_ex = run_extraction(
            extraction_id=ex.id, db=db_session, storage=tmp_storage, extractor=extractor,
        )
        assert result_ex.status == "completed"
        assert result_ex.canonical_data is not None
        assert result_ex.canonical_data["document_number"] == "TEST-1"
        assert result_ex.processing_time_ms == 1234
        assert result_ex.model_version == "claude-sonnet-4-6"
        assert result_ex.error_message is None
        extractor.extract.assert_called_once()

    def test_parse_failure_marks_failed(self, db_session, tmp_storage, tmp_path) -> None:
        s = _settings(tmp_path)
        doc, ex, _ = store_uploaded_file(
            content=b"pdf-bytes", filename="x.pdf", mime="application/pdf",
            storage=tmp_storage, db=db_session, settings=s,
        )
        extractor = _mock_extractor(_parse_fail_result())
        result_ex = run_extraction(
            extraction_id=ex.id, db=db_session, storage=tmp_storage, extractor=extractor,
        )
        assert result_ex.status == "failed"
        assert result_ex.canonical_data is None
        assert "json decode" in (result_ex.error_message or "")

    def test_exception_in_extractor_marks_failed(self, db_session, tmp_storage, tmp_path) -> None:
        s = _settings(tmp_path)
        doc, ex, _ = store_uploaded_file(
            content=b"pdf-bytes", filename="x.pdf", mime="application/pdf",
            storage=tmp_storage, db=db_session, settings=s,
        )
        extractor = MagicMock()
        extractor.model = "claude-sonnet-4-6"
        extractor.prompt_version = "v3"
        extractor.extract.side_effect = RuntimeError("api down")
        result_ex = run_extraction(
            extraction_id=ex.id, db=db_session, storage=tmp_storage, extractor=extractor,
        )
        assert result_ex.status == "failed"
        assert "RuntimeError: api down" in (result_ex.error_message or "")

    def test_unknown_extraction_id_raises(self, db_session, tmp_storage, tmp_path) -> None:
        extractor = _mock_extractor(_success_result())
        with pytest.raises(ExtractionServiceError, match="extraction not found"):
            run_extraction(
                extraction_id="non-existent-uuid",
                db=db_session, storage=tmp_storage, extractor=extractor,
            )


# ---------------------------------------------------------------------------
# create_reextract
# ---------------------------------------------------------------------------

class TestCreateReextract:
    def test_creates_new_pending_extraction(self, db_session, tmp_storage, tmp_path) -> None:
        s = _settings(tmp_path)
        doc, ex1, _ = store_uploaded_file(
            content=b"x", filename="x.pdf", mime="application/pdf",
            storage=tmp_storage, db=db_session, settings=s,
        )
        ex2 = create_reextract(document_id=doc.id, db=db_session, settings=s)
        assert ex2.id != ex1.id
        assert ex2.document_id == doc.id
        assert ex2.status == "pending"

    def test_missing_document_raises(self, db_session, tmp_storage, tmp_path) -> None:
        s = _settings(tmp_path)
        with pytest.raises(ExtractionServiceError, match="document not found"):
            create_reextract(document_id="nope", db=db_session, settings=s)

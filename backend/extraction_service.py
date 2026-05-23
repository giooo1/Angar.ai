"""Business logic for the extraction pipeline.

Sits between the HTTP route handlers (`backend/routes/extraction.py`)
and the shared extractor (`angar_extraction.Extractor`). Handles the
DB + storage persistence concerns the extractor itself knows nothing
about.

The Extractor is held as a module-level singleton (lazy-built on first
use) so the system prompt is loaded exactly once per process and the
Anthropic prompt-cache stays warm across requests.
"""

from __future__ import annotations

import tempfile
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from angar_extraction.extractor import Extractor, ExtractionResult
from backend.models import Document, Extraction
from backend.settings import Settings
from backend.storage import Storage, content_key, sha256_hex

_extractor_cache: Extractor | None = None


class ExtractionServiceError(Exception):
    """Raised for caller-fixable problems (file too big, wrong mime, etc.)."""


# ---------------------------------------------------------------------------
# Extractor singleton (model + prompt loaded once per process)
# ---------------------------------------------------------------------------

def get_extractor(settings: Settings) -> Extractor:
    """Lazy-build and cache one Extractor per process.

    Tests inject a fresh Extractor via reset_extractor() / set_extractor().
    """
    global _extractor_cache
    if _extractor_cache is None:
        _extractor_cache = Extractor(
            model=settings.angar_model,
            prompt_version=settings.angar_prompt_version,
            use_cache=settings.angar_use_cache,
        )
    return _extractor_cache


def set_extractor(extractor: Extractor | None) -> None:
    """Override (or clear) the cached Extractor. Test-only utility."""
    global _extractor_cache
    _extractor_cache = extractor


# ---------------------------------------------------------------------------
# Upload + extraction orchestration
# ---------------------------------------------------------------------------

def store_uploaded_file(
    *,
    content: bytes,
    filename: str,
    mime: str,
    storage: Storage,
    db: Session,
    settings: Settings,
    org_id: str,
    user_id: str,
) -> tuple[Document, Extraction, bool]:
    """Persist an uploaded file and create matching DB rows.

    Returns `(Document, Extraction, is_new)` where `is_new` is True when
    a fresh Document was created and False when an existing
    (org_id, file_sha256) row was reused. When reused, the latest
    Extraction for that Document is returned — caller decides whether
    to also re-extract.

    `org_id` and `user_id` are REQUIRED (step 5 auth). Routes pass the
    authenticated org/user; tests pass the test fixtures' ids.
    """
    if len(content) > settings.max_upload_bytes:
        raise ExtractionServiceError(
            f"file exceeds max upload size of {settings.max_upload_bytes} bytes"
        )
    if mime not in settings.allowed_mime_types:
        raise ExtractionServiceError(
            f"mime type {mime!r} not allowed; allowed: {settings.allowed_mime_types}"
        )

    file_sha = sha256_hex(content)

    existing = db.execute(
        select(Document).where(
            Document.organization_id == org_id,
            Document.file_sha256 == file_sha,
            Document.deleted_at.is_(None),
        )
    ).scalar_one_or_none()

    if existing is not None:
        latest = db.execute(
            select(Extraction)
            .where(Extraction.document_id == existing.id)
            .order_by(Extraction.created_at.desc())
        ).scalars().first()
        if latest is not None:
            return existing, latest, False
        # No prior extraction (edge: previous insert crashed). Make one.
        return existing, _create_extraction(existing, db, settings), False

    extension = _extension_for(mime)
    key = content_key(org_id, content, extension=extension)
    storage_path = storage.store(content, key)

    doc = Document(
        organization_id=org_id,
        uploaded_by_user_id=user_id,
        original_filename=filename,
        file_sha256=file_sha,
        file_size_bytes=len(content),
        file_mime_type=mime,
        storage_path=storage_path,
    )
    db.add(doc)
    db.flush()  # populates doc.id without committing yet

    extraction = _create_extraction(doc, db, settings)
    db.commit()
    db.refresh(doc)
    db.refresh(extraction)
    return doc, extraction, True


def run_extraction(
    *,
    extraction_id: str,
    db: Session,
    storage: Storage,
    extractor: Extractor,
) -> Extraction:
    """Execute extraction for the given Extraction row. Persist the result.

    Catches every exception so a single failed doc doesn't take down the
    request. On failure, sets status='failed' and `error_message`.
    """
    extraction = db.get(Extraction, extraction_id)
    if extraction is None:
        raise ExtractionServiceError(f"extraction not found: {extraction_id}")
    document = extraction.document

    extraction.status = "running"
    extraction.started_at = _utcnow()
    db.commit()

    try:
        pdf_bytes = storage.get(document.storage_path)
        # Extractor takes a Path; write to a tempfile in-place. The eval
        # Extractor interface is already file-based so we don't perturb it.
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(pdf_bytes)
            tmp_path = Path(tmp.name)
        try:
            result: ExtractionResult = extractor.extract(tmp_path)
        finally:
            tmp_path.unlink(missing_ok=True)

        extraction.model_version = extractor.model
        extraction.prompt_version = extractor.prompt_version
        extraction.processing_time_ms = result.processing_time_ms
        extraction.completed_at = _utcnow()

        if result.canonical is not None:
            extraction.canonical_data = result.canonical.model_dump(mode="json")
            extraction.warnings = []
            extraction.error_message = None
            extraction.status = "completed"
        else:
            extraction.canonical_data = None
            extraction.warnings = []
            extraction.error_message = result.parse_error or "extraction returned no canonical data"
            extraction.status = "failed"

    except Exception as exc:  # noqa: BLE001
        extraction.status = "failed"
        extraction.completed_at = _utcnow()
        extraction.error_message = f"{type(exc).__name__}: {exc}"

    db.commit()
    db.refresh(extraction)
    return extraction


def create_reextract(
    *,
    document_id: str,
    db: Session,
    settings: Settings,
) -> Extraction:
    """Create a new pending Extraction row for an existing document. No work yet."""
    doc = db.get(Document, document_id)
    if doc is None or doc.deleted_at is not None:
        raise ExtractionServiceError(f"document not found: {document_id}")
    extraction = _create_extraction(doc, db, settings)
    db.commit()
    db.refresh(extraction)
    return extraction


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_extraction(
    document: Document, db: Session, settings: Settings
) -> Extraction:
    extraction = Extraction(
        document_id=document.id,
        status="pending",
        prompt_version=settings.angar_prompt_version,
        model_version=settings.angar_model,
    )
    db.add(extraction)
    db.flush()
    return extraction


def _utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)


def _extension_for(mime: str) -> str:
    return {
        "application/pdf": "pdf",
        "image/jpeg": "jpg",
        "image/png": "png",
        "image/heic": "heic",
    }.get(mime, "bin")

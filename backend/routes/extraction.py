"""Extraction-path API endpoints (Phase 3 §3.3).

Three endpoints — upload, poll status, re-extract — wired against the
`extraction_service` module. Sync extraction inside the request handler
for now; the response shape is async-compatible so step 5+ can swap in
Celery without changing this contract.
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, File, HTTPException, Path, Query, Request, Response, UploadFile, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from backend import export_formats
from backend.models import _utcnow
from backend.rate_limit import limiter

from angar_extraction.extractor import Extractor
from angar_schema.canonical import CanonicalInvoice
from backend.api_schemas import (
    ApiError,
    BulkDeleteResponse,
    BulkIdsRequest,
    ErrorResponse,
    ExtractionStatusResponse,
    ListExtractionsResponse,
    UploadResponse,
)
from backend.auth import get_current_org, get_current_user
from backend.db import get_db
from backend.extraction_service import (
    ExtractionServiceError,
    create_reextract,
    get_extractor,
    run_extraction,
    store_uploaded_file,
)
from backend.models import Document, Extraction, Organization, User
from backend.quota import check_and_increment_quota, refund_quota
from backend.settings import Settings, get_settings
from backend.storage import FilesystemStorage, Storage

router = APIRouter()


# ---------------------------------------------------------------------------
# Dependencies (overridable by tests via app.dependency_overrides)
# ---------------------------------------------------------------------------

def get_settings_dep() -> Settings:
    return get_settings()


def get_storage(settings: Settings = Depends(get_settings_dep)) -> Storage:
    return FilesystemStorage(settings.storage_dir)


def get_extractor_dep(settings: Settings = Depends(get_settings_dep)) -> Extractor:
    return get_extractor(settings)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _bilingual_error(code: str, en: str, ka: str) -> ErrorResponse:
    return ErrorResponse(error=ApiError(code=code, message_en=en, message_ka=ka))


def _status_response(doc: Document, extraction: Extraction) -> ExtractionStatusResponse:
    return ExtractionStatusResponse(
        document_id=doc.id,
        extraction_id=extraction.id,
        status=extraction.status,  # type: ignore[arg-type]
        prompt_version=extraction.prompt_version,
        model_version=extraction.model_version,
        canonical_data=extraction.canonical_data,
        corrected_data=extraction.corrected_data,
        warnings=extraction.warnings or [],
        error_code=extraction.error_code,
        error_message=extraction.error_message,
        field_confidence=extraction.field_confidence or {},
        processing_time_ms=extraction.processing_time_ms,
        approved_at=extraction.approved_at,
    )


def _load_extraction_or_404(
    extraction_id: str, db: Session, current_org: Organization
) -> Extraction:
    """Fetch an extraction scoped to the caller's org, or raise 404.

    Same 404-not-403 posture as `get_extraction`: not-found and wrong-org are
    indistinguishable so we don't leak other orgs' ids.
    """
    extraction = db.get(Extraction, extraction_id)
    if extraction is None or extraction.document.organization_id != current_org.id:
        raise HTTPException(
            status_code=404,
            detail=_bilingual_error(
                "EXTRACTION_NOT_FOUND",
                f"Extraction {extraction_id} not found.",
                f"ექსტრაქცია {extraction_id} ვერ მოიძებნა.",
            ).model_dump(),
        )
    return extraction


# ---------------------------------------------------------------------------
# POST /documents — upload + extract
# ---------------------------------------------------------------------------

@router.post(
    "/documents",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=UploadResponse,
    responses={
        413: {"model": ErrorResponse},
        415: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
    },
)
@limiter.limit("30/minute")
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    storage: Storage = Depends(get_storage),
    extractor: Extractor = Depends(get_extractor_dep),
    settings: Settings = Depends(get_settings_dep),
    current_user: User = Depends(get_current_user),
    current_org: Organization = Depends(get_current_org),
) -> UploadResponse:
    content = await file.read()
    mime = file.content_type or "application/octet-stream"
    filename = file.filename or "upload.bin"

    # Quota gate: bump optimistically here, refund below if the upload
    # deduplicates onto an existing document (no model call needed).
    check_and_increment_quota(current_org)

    try:
        doc, extraction, is_new = store_uploaded_file(
            content=content,
            filename=filename,
            mime=mime,
            storage=storage,
            db=db,
            settings=settings,
            org_id=current_org.id,
            user_id=current_user.id,
        )
    except ExtractionServiceError as exc:
        # Validation failure (size / mime) — no model call was made.
        refund_quota(current_org)
        db.commit()
        # Differentiate the two 4xx causes: size vs mime type.
        message = str(exc)
        if "max upload size" in message:
            raise HTTPException(
                status_code=413,
                detail=_bilingual_error(
                    "FILE_TOO_LARGE",
                    f"File exceeds the {settings.max_upload_bytes} byte limit.",
                    f"ფაილი აღემატება ლიმიტს ({settings.max_upload_bytes} ბაიტი).",
                ).model_dump(),
            )
        if "mime type" in message:
            raise HTTPException(
                status_code=415,
                detail=_bilingual_error(
                    "INVALID_FILE_TYPE",
                    f"File type {mime} is not supported.",
                    f"ფაილის ფორმატი {mime} მხარდაჭერილი არ არის.",
                ).model_dump(),
            )
        raise HTTPException(
            status_code=400,
            detail=_bilingual_error("BAD_REQUEST", message, message).model_dump(),
        )

    # Sync extraction for fresh docs only — reusing a doc keeps its
    # existing extraction. Re-extract is a separate explicit endpoint.
    if is_new:
        extraction = run_extraction(
            extraction_id=extraction.id,
            db=db,
            storage=storage,
            extractor=extractor,
            current_org=current_org,
        )
    else:
        # Dedup: no new model call, so undo the quota bump.
        refund_quota(current_org)
        db.commit()

    return UploadResponse(
        document_id=doc.id,
        extraction_id=extraction.id,
        status=extraction.status,  # type: ignore[arg-type]
    )


# ---------------------------------------------------------------------------
# GET /extractions/{id} — poll
# ---------------------------------------------------------------------------

@router.get(
    "/extractions/{extraction_id}",
    response_model=ExtractionStatusResponse,
    responses={404: {"model": ErrorResponse}},
)
def get_extraction(
    extraction_id: str = Path(..., description="Extraction ID returned by upload."),
    db: Session = Depends(get_db),
    current_org: Organization = Depends(get_current_org),
) -> ExtractionStatusResponse:
    extraction = db.get(Extraction, extraction_id)
    if extraction is None or extraction.document.organization_id != current_org.id:
        # Same 404 for not-found vs wrong-org — no enumeration of other orgs' ids.
        raise HTTPException(
            status_code=404,
            detail=_bilingual_error(
                "EXTRACTION_NOT_FOUND",
                f"Extraction {extraction_id} not found.",
                f"ექსტრაქცია {extraction_id} ვერ მოიძებნა.",
            ).model_dump(),
        )
    return _status_response(extraction.document, extraction)


# ---------------------------------------------------------------------------
# POST /extractions/{id}/approve — human review sign-off
# ---------------------------------------------------------------------------

@router.post(
    "/extractions/{extraction_id}/approve",
    response_model=ExtractionStatusResponse,
    responses={404: {"model": ErrorResponse}},
)
def approve_extraction(
    extraction_id: str = Path(..., description="Extraction ID to approve."),
    db: Session = Depends(get_db),
    current_org: Organization = Depends(get_current_org),
) -> ExtractionStatusResponse:
    """Mark an extraction as reviewed-and-approved. Idempotent — re-approving
    just refreshes the timestamp."""
    extraction = _load_extraction_or_404(extraction_id, db, current_org)
    extraction.approved_at = _utcnow()
    db.commit()
    db.refresh(extraction)
    return _status_response(extraction.document, extraction)


# ---------------------------------------------------------------------------
# PUT /extractions/{id}/corrections — save reviewer edits
# ---------------------------------------------------------------------------

@router.put(
    "/extractions/{extraction_id}/corrections",
    response_model=ExtractionStatusResponse,
    responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def save_corrections(
    corrected: CanonicalInvoice,
    extraction_id: str = Path(...),
    db: Session = Depends(get_db),
    current_org: Organization = Depends(get_current_org),
) -> ExtractionStatusResponse:
    """Persist reviewer edits without touching the model's raw `canonical_data`.

    The body is validated against the canonical schema (FastAPI returns 422 on
    a malformed edit, e.g. a non-numeric amount), then stored normalized in
    `corrected_data`. Export and the review screen read corrected over raw.
    """
    extraction = _load_extraction_or_404(extraction_id, db, current_org)
    extraction.corrected_data = corrected.model_dump(mode="json")
    db.commit()
    db.refresh(extraction)
    return _status_response(extraction.document, extraction)


# ---------------------------------------------------------------------------
# GET /extractions/{id}/export — download as CSV / XLSX / JSON
# ---------------------------------------------------------------------------

_EXPORT_FORMATS: dict[str, tuple] = {
    "csv": (export_formats.to_csv, "text/csv; charset=utf-8", "csv"),
    "xlsx": (
        export_formats.to_xlsx,
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "xlsx",
    ),
    "json": (export_formats.to_json, "application/json", "json"),
}


def _safe_filename_base(extraction: Extraction) -> str:
    """ASCII-safe filename stem from the document number, falling back to the
    uploaded filename stem. Non-ASCII stripped so the `filename=` header is
    valid (Mkhedruli document numbers survive inside the file, not the name)."""
    canonical = extraction.corrected_data or extraction.canonical_data or {}
    raw = canonical.get("document_number") or extraction.document.original_filename or "export"
    raw = raw.rsplit(".", 1)[0]  # drop any extension on the fallback filename
    cleaned = "".join(c if (c.isascii() and (c.isalnum() or c in "-_")) else "_" for c in raw)
    cleaned = cleaned.strip("_") or "export"
    return cleaned


@router.get(
    "/extractions/{extraction_id}/export",
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
)
def export_extraction(
    extraction_id: str = Path(...),
    fmt: Literal["csv", "xlsx", "json"] = Query("csv", alias="format"),
    db: Session = Depends(get_db),
    current_org: Organization = Depends(get_current_org),
) -> Response:
    """Serialize a completed extraction's canonical data to a downloadable file.

    CSV/XLSX flatten to one row per line item; JSON is the full nested canonical.
    """
    extraction = _load_extraction_or_404(extraction_id, db, current_org)

    # Prefer reviewer corrections; fall back to the model's raw output.
    canonical = extraction.corrected_data or extraction.canonical_data
    if not canonical:
        # Exists, but never produced data (e.g. a failed extraction) — nothing
        # to export. 409: conflicts with the resource's current state.
        raise HTTPException(
            status_code=409,
            detail=_bilingual_error(
                "EXTRACTION_NOT_EXPORTABLE",
                "This extraction has no data to export.",
                "ამ ექსტრაქციას არ აქვს ექსპორტისთვის მონაცემები.",
            ).model_dump(),
        )

    serializer, media_type, ext = _EXPORT_FORMATS[fmt]
    content = serializer(canonical)
    filename = f"{_safe_filename_base(extraction)}.{ext}"
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ---------------------------------------------------------------------------
# Bulk archive actions — delete / export selected
# ---------------------------------------------------------------------------

def _owned_extractions(ids: list[str], db: Session, current_org: Organization) -> list[Extraction]:
    """Caller-owned, non-deleted extractions in `ids` (newest first). Silently
    drops ids from other orgs — no error, no existence leak."""
    if not ids:
        return []
    return list(
        db.execute(
            select(Extraction)
            .join(Document, Extraction.document_id == Document.id)
            .where(Extraction.id.in_(ids))
            .where(Document.organization_id == current_org.id)
            .where(Document.deleted_at.is_(None))
            .order_by(Extraction.created_at.desc())
        ).scalars().all()
    )


@router.post("/extractions/bulk-delete", response_model=BulkDeleteResponse)
def bulk_delete(
    body: BulkIdsRequest,
    db: Session = Depends(get_db),
    current_org: Organization = Depends(get_current_org),
) -> BulkDeleteResponse:
    """Soft-delete the documents behind the selected extractions (recoverable —
    hidden from lists via Document.deleted_at). Idempotent; org-gated."""
    rows = _owned_extractions(body.extraction_ids, db, current_org)
    docs = {r.document_id: r.document for r in rows}  # dedupe per document
    now = _utcnow()
    for doc in docs.values():
        doc.deleted_at = now
    db.commit()
    return BulkDeleteResponse(deleted=len(docs))


@router.post("/extractions/bulk-export")
def bulk_export(
    body: BulkIdsRequest,
    db: Session = Depends(get_db),
    current_org: Organization = Depends(get_current_org),
) -> Response:
    """Combined CSV of the selected documents' line items (one shared header).
    Reads corrected-over-raw per doc; skips any with no canonical data."""
    if not body.extraction_ids:
        raise HTTPException(
            status_code=400,
            detail=_bilingual_error(
                "NO_SELECTION", "No documents selected.", "დოკუმენტები არ არის არჩეული."
            ).model_dump(),
        )
    if len(body.extraction_ids) > 500:
        raise HTTPException(
            status_code=400,
            detail=_bilingual_error(
                "TOO_MANY", "Select at most 500 documents.", "აირჩიეთ მაქსიმუმ 500 დოკუმენტი."
            ).model_dump(),
        )
    rows = _owned_extractions(body.extraction_ids, db, current_org)
    canonicals = [r.corrected_data or r.canonical_data for r in rows if (r.corrected_data or r.canonical_data)]
    content = export_formats.to_combined_csv(canonicals)
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="documents-export.csv"'},
    )


# ---------------------------------------------------------------------------
# POST /documents/{id}/extract — re-extract
# ---------------------------------------------------------------------------

@router.post(
    "/documents/{document_id}/extract",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=UploadResponse,
    responses={404: {"model": ErrorResponse}},
)
def reextract_document(
    document_id: str = Path(...),
    db: Session = Depends(get_db),
    storage: Storage = Depends(get_storage),
    extractor: Extractor = Depends(get_extractor_dep),
    settings: Settings = Depends(get_settings_dep),
    current_org: Organization = Depends(get_current_org),
) -> UploadResponse:
    # Verify org ownership before kicking off a new extraction.
    doc = db.get(Document, document_id)
    if doc is None or doc.organization_id != current_org.id:
        raise HTTPException(
            status_code=404,
            detail=_bilingual_error(
                "DOCUMENT_NOT_FOUND",
                f"Document {document_id} not found.",
                f"დოკუმენტი {document_id} ვერ მოიძებნა.",
            ).model_dump(),
        )

    # Re-extract always calls the model — counts against quota.
    check_and_increment_quota(current_org)

    try:
        extraction = create_reextract(
            document_id=document_id, db=db, settings=settings
        )
    except ExtractionServiceError:
        # Doc disappeared between the org check and create_reextract —
        # no model call happened, return the quota bump.
        refund_quota(current_org)
        db.commit()
        raise HTTPException(
            status_code=404,
            detail=_bilingual_error(
                "DOCUMENT_NOT_FOUND",
                f"Document {document_id} not found.",
                f"დოკუმენტი {document_id} ვერ მოიძებნა.",
            ).model_dump(),
        )
    extraction = run_extraction(
        extraction_id=extraction.id,
        db=db,
        storage=storage,
        extractor=extractor,
        current_org=current_org,
    )
    return UploadResponse(
        document_id=document_id,
        extraction_id=extraction.id,
        status=extraction.status,  # type: ignore[arg-type]
    )


# ---------------------------------------------------------------------------
# GET /documents/{id}/file — stream the original upload
# ---------------------------------------------------------------------------

@router.get(
    "/documents/{document_id}/file",
    responses={404: {"model": ErrorResponse}},
)
def get_document_file(
    document_id: str = Path(...),
    db: Session = Depends(get_db),
    storage: Storage = Depends(get_storage),
    current_org: Organization = Depends(get_current_org),
) -> Response:
    """Stream the original uploaded PDF/image bytes back to the client.

    Gated by the current organization — a doc belonging to a different
    org returns 404 (not 403) so we don't leak existence to other orgs.
    """
    doc = db.get(Document, document_id)
    if (
        doc is None
        or doc.deleted_at is not None
        or doc.organization_id != current_org.id
    ):
        raise HTTPException(
            status_code=404,
            detail=_bilingual_error(
                "DOCUMENT_NOT_FOUND",
                f"Document {document_id} not found.",
                f"დოკუმენტი {document_id} ვერ მოიძებნა.",
            ).model_dump(),
        )
    try:
        content = storage.get(doc.storage_path)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=404,
            detail=_bilingual_error(
                "DOCUMENT_FILE_MISSING",
                f"Document content not found in storage: {exc}",
                f"დოკუმენტის ფაილი ვერ მოიძებნა საცავში.",
            ).model_dump(),
        ) from exc

    # Inline so the iframe renders the PDF rather than downloading it.
    # Filename escaped via quote() so non-ASCII (Georgian) names survive.
    safe_name = doc.original_filename.replace('"', "")
    return Response(
        content=content,
        media_type=doc.file_mime_type,
        headers={
            "Content-Disposition": f'inline; filename="{safe_name}"',
            "Cache-Control": "private, max-age=60",
        },
    )


# ---------------------------------------------------------------------------
# GET /extractions — paginated list (for the Review queue)
# ---------------------------------------------------------------------------

@router.get(
    "/extractions",
    response_model=ListExtractionsResponse,
)
def list_extractions(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    pending: bool = Query(False, description="Only docs needing attention (not yet approved)."),
    sort: Literal["newest", "oldest"] = Query("newest"),
    q: str | None = Query(None, description="Search filename / document number / seller name."),
    document_type: str | None = Query(None),
    accepted: bool | None = Query(None),
    has_corrections: bool = Query(False),
    date_from: str | None = Query(None, description="Invoice date >= (YYYY-MM-DD)."),
    date_to: str | None = Query(None, description="Invoice date <= (YYYY-MM-DD)."),
    db: Session = Depends(get_db),
    current_org: Organization = Depends(get_current_org),
) -> ListExtractionsResponse:
    """List extractions for the caller's org.

    The worklist calls `pending=true&sort=oldest` (FIFO over docs awaiting
    review — approval clears them); the archive uses the defaults (everything,
    newest first) plus search/filters. When `pending`, `total` is the
    needs-attention count; otherwise `total` reflects any active filters.
    Page size capped at 100 so a misbehaving client can't pull the whole
    table at once.

    Filters match the raw `canonical_data` classification (corrections to
    type/accepted are rare and not reflected in filtering for v1).
    """
    org_id = current_org.id

    def _json(path: str):
        return func.json_extract(Extraction.canonical_data, path)

    base = (
        select(Extraction)
        .join(Document, Extraction.document_id == Document.id)
        .where(Document.organization_id == org_id)
        .where(Document.deleted_at.is_(None))
    )
    if pending:
        # "Needs attention" = not yet approved (covers failed + extracted-but-
        # -unverified). Approving sets approved_at, removing it from the queue.
        base = base.where(Extraction.approved_at.is_(None))
    if q:
        like = f"%{q}%"
        base = base.where(
            or_(
                Document.original_filename.ilike(like),
                _json("$.document_number").ilike(like),
                _json("$.seller.name").ilike(like),
            )
        )
    if document_type:
        base = base.where(_json("$.document_type") == document_type)
    if accepted is not None:
        # SQLite json_extract returns 1/0 for JSON booleans.
        base = base.where(_json("$.accepted") == (1 if accepted else 0))
    if has_corrections:
        base = base.where(Extraction.corrected_data.is_not(None))
    if date_from:
        base = base.where(_json("$.document_date") >= date_from)
    if date_to:
        base = base.where(_json("$.document_date") <= date_to)

    total = db.execute(
        select(func.count()).select_from(base.subquery())
    ).scalar_one()

    order = Extraction.created_at.asc() if sort == "oldest" else Extraction.created_at.desc()
    rows = db.execute(
        base.order_by(order)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).scalars().all()

    items = [_status_response(r.document, r) for r in rows]

    return ListExtractionsResponse(
        items=items,
        total=int(total),
        page=page,
        page_size=page_size,
    )

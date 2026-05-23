"""Extraction-path API endpoints (Phase 3 §3.3).

Three endpoints — upload, poll status, re-extract — wired against the
`extraction_service` module. Sync extraction inside the request handler
for now; the response shape is async-compatible so step 5+ can swap in
Celery without changing this contract.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, Path, Query, Response, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from angar_extraction.extractor import Extractor
from backend.api_schemas import (
    ApiError,
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
        warnings=extraction.warnings or [],
        error_message=extraction.error_message,
        processing_time_ms=extraction.processing_time_ms,
    )


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
    },
)
async def upload_document(
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
        )

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
    try:
        extraction = create_reextract(
            document_id=document_id, db=db, settings=settings
        )
    except ExtractionServiceError:
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
    db: Session = Depends(get_db),
    current_org: Organization = Depends(get_current_org),
) -> ListExtractionsResponse:
    """List recent extractions, newest first, filtered to the caller's org.

    Page size capped at 100 so a misbehaving client can't pull the whole
    table at once.
    """
    org_id = current_org.id

    base = (
        select(Extraction)
        .join(Document, Extraction.document_id == Document.id)
        .where(Document.organization_id == org_id)
    )

    total = db.execute(
        select(func.count()).select_from(base.subquery())
    ).scalar_one()

    rows = db.execute(
        base.order_by(Extraction.created_at.desc())
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

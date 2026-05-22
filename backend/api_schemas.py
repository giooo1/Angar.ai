"""Pydantic models for the FastAPI request/response surface.

Shape matches Phase 3 §3.3 exactly so the future Next.js UI doesn't
need to change when this server swaps sync extraction for Celery async.
The `status` field is the contract: it can already be "pending" /
"running" / "completed" / "failed" even though for now most responses
will show "completed" immediately.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

ExtractionStatus = Literal["pending", "running", "completed", "failed"]


class UploadResponse(BaseModel):
    """Returned by POST /api/v1/documents (202 Accepted)."""

    document_id: str
    extraction_id: str
    status: ExtractionStatus


class ExtractionStatusResponse(BaseModel):
    """Returned by GET /api/v1/extractions/{id}."""

    document_id: str
    extraction_id: str
    status: ExtractionStatus
    prompt_version: str
    model_version: str
    canonical_data: dict[str, Any] | None = None
    warnings: list[str] = Field(default_factory=list)
    error_message: str | None = None
    processing_time_ms: int | None = None


class ListExtractionsResponse(BaseModel):
    """Returned by GET /api/v1/extractions — paginated list."""

    items: list[ExtractionStatusResponse]
    total: int
    page: int
    page_size: int


class ApiError(BaseModel):
    """Inner error payload per Phase 3 §3.1."""

    code: str
    message_en: str
    message_ka: str


class ErrorResponse(BaseModel):
    """Top-level error envelope per Phase 3 §3.1."""

    error: ApiError

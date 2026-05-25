"""Pydantic models for the FastAPI request/response surface.

Shape matches Phase 3 §3.3 exactly so the future Next.js UI doesn't
need to change when this server swaps sync extraction for Celery async.
The `status` field is the contract: it can already be "pending" /
"running" / "completed" / "failed" even though for now most responses
will show "completed" immediately.
"""

from __future__ import annotations

from datetime import datetime
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
    error_code: str | None = None
    error_message: str | None = None
    field_confidence: dict[str, float] = Field(default_factory=dict)
    processing_time_ms: int | None = None
    approved_at: datetime | None = None


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


# ---------------------------------------------------------------------------
# Auth DTOs (Phase 4 step 5)
# ---------------------------------------------------------------------------


class RegisterRequest(BaseModel):
    """Body of POST /api/v1/auth/register."""

    email: str
    password: str
    full_name: str | None = None
    organization_name: str


class LoginRequest(BaseModel):
    """Body of POST /api/v1/auth/login."""

    email: str
    password: str


class VerifyEmailRequest(BaseModel):
    """Body of POST /api/v1/auth/verify-email."""

    token: str


class RequestPasswordResetRequest(BaseModel):
    """Body of POST /api/v1/auth/request-password-reset."""

    email: str


class ResetPasswordRequest(BaseModel):
    """Body of POST /api/v1/auth/reset-password."""

    token: str
    new_password: str


class UserDTO(BaseModel):
    """Public-facing user shape. Never includes the password hash."""

    id: str
    email: str
    full_name: str | None
    locale: str
    email_verified_at: datetime | None = None


class OrganizationDTO(BaseModel):
    """Public-facing organization shape. Includes live quota (step 6)."""

    id: str
    name: str
    plan: str
    monthly_extraction_quota: int
    monthly_extractions_used: int
    quota_reset_at: datetime


class SessionResponse(BaseModel):
    """Returned by POST /auth/register, POST /auth/login, GET /me."""

    user: UserDTO
    organization: OrganizationDTO

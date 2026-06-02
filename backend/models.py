"""SQLAlchemy ORM models for the backend.

Mirrors Phase 3 §2.2 (documents, extractions) using SQLite-compatible
types. On the Postgres swap later, the JSON columns become JSONB but
nothing else needs changing.

Multi-tenancy: every row carries `organization_id`. While auth isn't
landed yet (step 5), the column exists with a stubbed default so the
schema doesn't need migrating once real orgs / users come online.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db import Base


def _uuid_str() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)


def _retention_default() -> datetime:
    # 30 days from now. Matches settings.retention_days but resolved at
    # row-creation time, not import time. Settings injection happens at
    # the service layer; the model uses a sensible default.
    return _utcnow() + timedelta(days=30)


# ---------------------------------------------------------------------------
# Auth tables (Phase 4 step 5)
# ---------------------------------------------------------------------------


class User(Base):
    """A real human account. argon2id-hashed password lives here.

    Email is the login identity and must be unique. Multi-org membership
    isn't supported in step 5 — every user belongs to exactly one org.
    """

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid_str)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    locale: Mapped[str] = mapped_column(String(8), default="en")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    memberships: Mapped[list["OrganizationMember"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    email_tokens: Mapped[list["EmailToken"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Organization(Base):
    """A workspace. Documents and extractions belong to an organization, not a user.

    Quota fields (step 6): rolling 30-day window. `quota_reset_at` is set
    at registration time to `created_at + 30 days` and lazily rolled
    forward by `backend.quota.reset_if_due` whenever an upload is gated.
    """

    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid_str)
    name: Mapped[str] = mapped_column(String(255))
    plan: Mapped[str] = mapped_column(String(16), default="free")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    monthly_extraction_quota: Mapped[int] = mapped_column(Integer, default=25)
    monthly_extractions_used: Mapped[int] = mapped_column(Integer, default=0)
    quota_reset_at: Mapped[datetime] = mapped_column(
        DateTime, default=_retention_default
    )

    # Stripe linkage (Phase 4.5 WS5). NULL while the org hasn't paid.
    stripe_customer_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    members: Mapped[list["OrganizationMember"]] = relationship(
        back_populates="organization", cascade="all, delete-orphan"
    )


class WebhookEvent(Base):
    """Idempotency record for Stripe webhooks (Phase 4.5 WS5).

    Stripe can deliver the same event multiple times under retry policy.
    Before processing an event we INSERT this row keyed by the event id;
    if the INSERT collides on the PK, the second delivery acks 200 and
    does nothing. `processed_at` is informational only.
    """

    __tablename__ = "webhook_events"

    # Stripe event ids are short strings like `evt_1OabcDeFghIj`.
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    type: Mapped[str] = mapped_column(String(64))
    received_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class EmailToken(Base):
    """One-time tokens for email verification and password reset (WS4).

    Storing `token_hash` (sha256) rather than the raw token: a DB leak
    doesn't immediately let an attacker mint sessions for every pending
    verify/reset. The raw token only ever appears in the email body.
    """

    __tablename__ = "email_tokens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid_str)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    purpose: Mapped[str] = mapped_column(String(16))  # "verify" | "reset"
    token_hash: Mapped[str] = mapped_column(String(64), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    user: Mapped["User"] = relationship(back_populates="email_tokens")


class OrganizationMember(Base):
    """Join row between User and Organization with a per-org role."""

    __tablename__ = "organization_members"

    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    role: Mapped[str] = mapped_column(String(16), default="member")  # owner | admin | member
    joined_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    user: Mapped["User"] = relationship(back_populates="memberships")
    organization: Mapped["Organization"] = relationship(back_populates="members")


# ---------------------------------------------------------------------------
# Document + Extraction
# ---------------------------------------------------------------------------


class Document(Base):
    """One row per uploaded file. Dedup by (organization_id, file_sha256)."""

    __tablename__ = "documents"
    __table_args__ = (
        UniqueConstraint("organization_id", "file_sha256", name="uq_doc_org_sha"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid_str)

    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    uploaded_by_user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT")
    )

    original_filename: Mapped[str] = mapped_column(String(512))
    file_sha256: Mapped[str] = mapped_column(String(64), index=True)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger)
    file_mime_type: Mapped[str] = mapped_column(String(64))
    storage_path: Mapped[str] = mapped_column(String(512))

    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    delete_at: Mapped[datetime] = mapped_column(DateTime, default=_retention_default)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    extractions: Mapped[list["Extraction"]] = relationship(
        back_populates="document",
        order_by="Extraction.created_at.desc()",
        cascade="all, delete-orphan",
    )


class Extraction(Base):
    """One row per extraction attempt against a Document. Multiple per doc allowed."""

    __tablename__ = "extractions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid_str)
    document_id: Mapped[str] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )

    status: Mapped[str] = mapped_column(
        String(16), default="pending"
    )  # pending | running | completed | failed
    prompt_version: Mapped[str] = mapped_column(String(64))
    model_version: Mapped[str] = mapped_column(String(64))

    canonical_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    field_confidence: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    warnings: Mapped[list[str]] = mapped_column(JSON, default=list)
    error_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(4096), nullable=True)

    processing_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    # Human review sign-off — set when a reviewer clicks Approve. Distinct
    # from `status` (extraction lifecycle) and `canonical.accepted` (the
    # model's own is-this-an-invoice judgment). Null until approved.
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Reviewer corrections to the extracted data. Null until the user saves
    # an edit. `canonical_data` always preserves the model's raw output (eval
    # signal); export and the review screen read `corrected_data or canonical_data`.
    corrected_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    document: Mapped["Document"] = relationship(back_populates="extractions")

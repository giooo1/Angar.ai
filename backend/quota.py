"""Quota enforcement (Phase 4 step 6).

Free-plan accounts get N extractions per 30-day rolling window. The
counter resets lazily on every quota check, so no background job is
needed. When the cap is hit, callers get HTTP 429 with a structured
detail the frontend can render as a "quota exhausted" empty state.

Used by `backend/routes/extraction.py` — upload and re-extract paths
both call `check_and_increment_quota` before they spend a model call.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from backend.models import Organization

_ROLL = timedelta(days=30)


def _utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)


def _as_aware(dt: datetime) -> datetime:
    # SQLite drops tzinfo on round-trip. Treat naive timestamps as UTC.
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def reset_if_due(org: Organization) -> None:
    """If the rolling window has elapsed, zero the counter and roll forward.

    Bumps `quota_reset_at` by 30-day increments until it's in the future.
    Handles the case where an org is dormant for multiple cycles — the
    counter still ends at 0 and the next reset is at most 30 days out.

    Does not commit; the caller's transaction picks up the change.
    """
    now = _utcnow()
    reset_at = _as_aware(org.quota_reset_at)
    if reset_at > now:
        return
    while reset_at <= now:
        reset_at += _ROLL
    org.quota_reset_at = reset_at
    org.monthly_extractions_used = 0


def check_and_increment_quota(org: Organization) -> None:
    """Roll the window if due, raise 429 if exhausted, else increment.

    Side effects: mutates `org.monthly_extractions_used` (and possibly
    `org.quota_reset_at`). The caller is responsible for `db.commit()`.
    """
    reset_if_due(org)
    quota = org.monthly_extraction_quota
    if org.monthly_extractions_used >= quota:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": {
                    "code": "QUOTA_EXHAUSTED",
                    "message_en": "Monthly extraction quota reached.",
                    "message_ka": "თვის ექსტრაქციების ლიმიტი ამოწურულია.",
                },
                "quota": quota,
                "used": org.monthly_extractions_used,
                "resets_at": _as_aware(org.quota_reset_at).isoformat(),
            },
        )
    org.monthly_extractions_used += 1


def refund_quota(org: Organization) -> None:
    """Roll the increment back. Used when an upload deduplicates and the
    quota bump turned out to be unwarranted. Never goes below zero.
    """
    if org.monthly_extractions_used > 0:
        org.monthly_extractions_used -= 1

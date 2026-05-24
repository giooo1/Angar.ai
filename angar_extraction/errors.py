"""Typed exceptions for the extraction pipeline.

The Anthropic SDK raises a handful of `APIStatusError` subclasses keyed
by HTTP status. The eval harness and the FastAPI route layer each want
to react differently to those — retry transient errors, refund quota
for infra failures, return a specific frontend-friendly code for bad
PDFs. This module translates SDK exceptions into a small fixed set the
rest of the codebase pattern-matches on.

Error-code strings are stable; the frontend renders different copy per
code.  Adding a new code means adding a new branch in
`extraction_service.run_extraction`'s exception dispatch and a new
case in the frontend review UI.
"""

from __future__ import annotations


class ExtractionError(Exception):
    """Base for every Angar-defined extraction failure."""

    code: str = "UNKNOWN"
    is_transient: bool = False


class AnthropicAuthError(ExtractionError):
    """SDK rejected the API key (401). Operator problem, not the user's."""

    code = "ANTHROPIC_AUTH"
    is_transient = False


class AnthropicRateLimitError(ExtractionError):
    """SDK reported rate-limit (429). Retry with backoff before surfacing."""

    code = "ANTHROPIC_RATE_LIMIT"
    is_transient = True


class AnthropicOverloadedError(ExtractionError):
    """Anthropic-side capacity issue (529 / overloaded). Retry."""

    code = "ANTHROPIC_OVERLOADED"
    is_transient = True


class AnthropicAPIError(ExtractionError):
    """Catch-all for other SDK errors (timeouts, 5xx, connection). Retry."""

    code = "ANTHROPIC_API"
    is_transient = True


class MalformedPDFError(ExtractionError):
    """SDK refused the input — the document itself was unprocessable.

    Not transient. The user needs a better scan, not a retry. This still
    consumes quota: the model call was attempted and Anthropic decided.
    """

    code = "MALFORMED_PDF"
    is_transient = False


# Map ExtractionError.code -> consumer-facing en/ka copy. Frontend pulls
# the structured `error_code` and renders its own strings; backend uses
# this only for `error_message` fallback.
ERROR_COPY: dict[str, tuple[str, str]] = {
    "ANTHROPIC_AUTH": (
        "Backend misconfiguration. Your quota was refunded.",
        "სერვერის კონფიგურაცია. ლიმიტი დაგიბრუნდათ.",
    ),
    "ANTHROPIC_RATE_LIMIT": (
        "Service is busy. We retried but failed; your quota was refunded.",
        "სერვისი დატვირთულია. სცადეთ მოგვიანებით — ლიმიტი დაგიბრუნდათ.",
    ),
    "ANTHROPIC_OVERLOADED": (
        "Service is temporarily overloaded; your quota was refunded.",
        "სერვისი დროებით გადატვირთულია — ლიმიტი დაგიბრუნდათ.",
    ),
    "ANTHROPIC_API": (
        "Couldn't reach the extraction service. Your quota was refunded.",
        "ექსტრაქციის სერვისთან კავშირი ვერ მოხერხდა — ლიმიტი დაგიბრუნდათ.",
    ),
    "MALFORMED_PDF": (
        "Couldn't read this document — try a clearer scan.",
        "დოკუმენტი ვერ წავიკითხეთ — სცადეთ უფრო მკაფიო სკანი.",
    ),
    "PARSE_ERROR": (
        "Model returned data we couldn't parse. Try re-extracting.",
        "მოდელის პასუხი ვერ დავამუშავეთ — სცადეთ ხელახლა.",
    ),
    "UNKNOWN": (
        "Something went wrong. Your quota was refunded.",
        "რაღაც შეცდომა მოხდა — ლიმიტი დაგიბრუნდათ.",
    ),
}

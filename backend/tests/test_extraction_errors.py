"""Tests for typed extraction-error dispatch + quota refund (WS2).

For each error class:
- the Extraction row ends up with `status='failed'` and the right `error_code`
- infrastructure failures refund the quota slot
- PDF-side failures (MALFORMED_PDF, PARSE_ERROR) do NOT refund — model
  was called and Anthropic decided
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from angar_extraction.errors import (
    AnthropicAPIError,
    AnthropicAuthError,
    AnthropicOverloadedError,
    AnthropicRateLimitError,
    ExtractionError,
    MalformedPDFError,
)
from angar_extraction.extractor import ExtractionResult
from backend.auth import get_current_org, get_current_user
from backend.db import get_db
from backend.main import app
from backend.routes.extraction import (
    get_extractor_dep,
    get_settings_dep,
    get_storage,
)
from backend.settings import Settings


def _empty_result() -> ExtractionResult:
    """A result that successfully parsed (used by tests that don't raise)."""
    return ExtractionResult(
        canonical=None,
        raw_response="garbage",
        input_tokens=10,
        cached_input_tokens=0,
        output_tokens=10,
        processing_time_ms=100,
        parse_error="schema validation: missing required field",
    )


@pytest.fixture
def client_with_error(db_session, tmp_storage, tmp_path, test_user, test_org):
    """TestClient where the extractor raises whatever the test's `raising_extractor`
    fixture is wired to raise. Each test parametrizes the exception."""
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'test.db'}",
        storage_dir=tmp_path / "files",
        anthropic_api_key="sk-test-not-real",
        jwt_secret="test-jwt-secret",
    )

    mock_extractor = MagicMock()
    mock_extractor.model = "claude-sonnet-4-6"
    mock_extractor.prompt_version = "v3"

    def _db_override():
        yield db_session

    app.dependency_overrides[get_db] = _db_override
    app.dependency_overrides[get_storage] = lambda: tmp_storage
    app.dependency_overrides[get_extractor_dep] = lambda: mock_extractor
    app.dependency_overrides[get_settings_dep] = lambda: settings
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_current_org] = lambda: test_org

    yield TestClient(app), mock_extractor

    app.dependency_overrides.clear()


def _trigger_upload(tc: TestClient, content: bytes = b"%PDF-1.4 trigger") -> dict:
    """Drive one upload and return the parsed JSON response body."""
    r = tc.post(
        "/api/v1/documents",
        files={"file": ("err.pdf", content, "application/pdf")},
    )
    assert r.status_code in (202, 429), r.text
    return r.json() if r.status_code == 202 else {}


@pytest.mark.parametrize(
    "exc, expected_code, expect_refund",
    [
        (AnthropicAuthError("no key"), "ANTHROPIC_AUTH", True),
        (AnthropicRateLimitError("slow down"), "ANTHROPIC_RATE_LIMIT", True),
        (AnthropicOverloadedError("529"), "ANTHROPIC_OVERLOADED", True),
        (AnthropicAPIError("timeout"), "ANTHROPIC_API", True),
        (MalformedPDFError("bad input"), "MALFORMED_PDF", False),
        (RuntimeError("???"), "UNKNOWN", True),
    ],
)
def test_extractor_error_persists_code_and_handles_refund(
    client_with_error, db_session, test_org, exc, expected_code, expect_refund
):
    tc, mock_extractor = client_with_error
    mock_extractor.extract.side_effect = exc
    pre = test_org.monthly_extractions_used

    _trigger_upload(tc)

    db_session.refresh(test_org)
    if expect_refund:
        assert test_org.monthly_extractions_used == pre, (
            f"expected refund for {expected_code}; used went {pre}→"
            f"{test_org.monthly_extractions_used}"
        )
    else:
        assert test_org.monthly_extractions_used == pre + 1, (
            f"did not expect refund for {expected_code}; used should bump"
        )

    # And the Extraction row carries the right error_code + status.
    from backend.models import Extraction
    row = db_session.query(Extraction).order_by(Extraction.created_at.desc()).first()
    assert row is not None
    assert row.status == "failed"
    assert row.error_code == expected_code


def test_parse_error_persists_code_and_consumes_quota(
    client_with_error, db_session, test_org
):
    """Parse failures (model returned something, but unparseable) do NOT refund."""
    tc, mock_extractor = client_with_error
    mock_extractor.extract.return_value = _empty_result()
    pre = test_org.monthly_extractions_used

    _trigger_upload(tc)

    db_session.refresh(test_org)
    assert test_org.monthly_extractions_used == pre + 1

    from backend.models import Extraction
    row = db_session.query(Extraction).order_by(Extraction.created_at.desc()).first()
    assert row is not None
    assert row.status == "failed"
    assert row.error_code == "PARSE_ERROR"


def test_extractor_retries_transient_then_succeeds(tmp_path):
    """The extractor's retry loop succeeds on the 2nd attempt for a rate-limit."""
    from anthropic import RateLimitError
    from angar_extraction.extractor import Extractor

    fake_response_value = MagicMock()
    fake_response_value.content = [MagicMock(text='{"accepted": true}')]
    fake_response_value.usage.input_tokens = 1
    fake_response_value.usage.cache_read_input_tokens = 0
    fake_response_value.usage.output_tokens = 1

    client = MagicMock()
    rl_err = RateLimitError(
        message="slow down",
        response=MagicMock(status_code=429, headers={}),
        body=None,
    )
    client.messages.create.side_effect = [rl_err, fake_response_value]

    extractor = Extractor(
        model="claude-haiku-4-5-20251001",
        prompt_version="v3",
        use_cache=False,
        client=client,
    )
    # Compress the backoff so this test is fast.
    extractor._RETRY_BASE_SECONDS = 0.0  # type: ignore[attr-defined]

    pdf_path = tmp_path / "x.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 x")

    result = extractor.extract(pdf_path)
    assert result.parse_error is not None or result.canonical is not None
    # Either way: the SDK was called twice.
    assert client.messages.create.call_count == 2


def test_extractor_raises_typed_auth_error_after_retries_exhausted(tmp_path):
    """Auth errors are not transient — first attempt re-raises as typed exc."""
    from anthropic import AuthenticationError
    from angar_extraction.extractor import Extractor

    client = MagicMock()
    client.messages.create.side_effect = AuthenticationError(
        message="bad key",
        response=MagicMock(status_code=401, headers={}),
        body=None,
    )
    extractor = Extractor(
        model="claude-haiku-4-5-20251001",
        prompt_version="v3",
        use_cache=False,
        client=client,
    )
    pdf_path = tmp_path / "x.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 x")

    with pytest.raises(AnthropicAuthError):
        extractor.extract(pdf_path)
    # No retry on auth: exactly one SDK call.
    assert client.messages.create.call_count == 1

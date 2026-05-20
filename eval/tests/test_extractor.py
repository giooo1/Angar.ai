"""Unit tests for eval.extractor.

These tests inject a mock Anthropic client so they don't hit the real API.
What we verify:
- The system prompt is wrapped with cache_control by default; not when use_cache=False
- The user message contains the PDF as a base64 document content block
- The model name and max_tokens flow through to messages.create
- Response parsing: JSON-fenced, bare JSON, and parse-failure paths
- Token usage is read from the response's usage.{input,output,cache_read}_tokens
"""

from __future__ import annotations

import base64
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest

from eval import canonical_path  # noqa: F401
from eval import extractor as extractor_module
from eval import prompt as prompt_module
from eval.extractor import (  # noqa: E402
    Extractor,
    _extract_first_json_object,
    _try_parse_canonical,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _valid_canonical_json_dict() -> dict[str, Any]:
    """Smallest CanonicalInvoice that validates (mirrors test_fixtures helper)."""
    return {
        "accepted": True,
        "document_type": "regular_invoice",
        "document_number": "TEST-1",
        "document_date": "2026-01-01",
        "document_currency": "GEL",
        "items": [],
        "extraction": {
            "source_filename": "fake.pdf",
            "source_pdf_sha256": "deadbeef",
            "extracted_at": "2026-01-01T00:00:00Z",
            "model_version": "test",
            "prompt_version": "test",
        },
    }


@pytest.fixture
def real_prompt(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Replace eval/prompts with a tmp dir holding a non-placeholder prompt."""
    prompts = tmp_path / "prompts"
    prompts.mkdir()
    (prompts / "v0.md").write_text("You are an invoice extraction assistant.", encoding="utf-8")
    monkeypatch.setattr(prompt_module, "PROMPTS_DIR", prompts)
    return prompts


@pytest.fixture
def mock_client_response() -> MagicMock:
    """Build a mock Anthropic message response with usage metadata."""
    mock = MagicMock()
    mock.content = [SimpleNamespace(text=json.dumps(_valid_canonical_json_dict()))]
    mock.usage = SimpleNamespace(
        input_tokens=1000,
        output_tokens=500,
        cache_read_input_tokens=800,
    )
    return mock


@pytest.fixture
def mock_client(mock_client_response: MagicMock) -> MagicMock:
    client = MagicMock()
    client.messages.create.return_value = mock_client_response
    return client


@pytest.fixture
def sample_pdf(tmp_path: Path) -> Path:
    pdf = tmp_path / "sample.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake content for testing")
    return pdf


# ---------------------------------------------------------------------------
# Construction and prompt loading
# ---------------------------------------------------------------------------

class TestConstruction:
    def test_loads_prompt_during_init(
        self, real_prompt: Path, mock_client: MagicMock
    ) -> None:
        e = Extractor(model="claude-sonnet-4-6", prompt_version="v0", client=mock_client)
        assert e.system_prompt == "You are an invoice extraction assistant."

    def test_init_raises_on_placeholder_prompt(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mock_client: MagicMock
    ) -> None:
        prompts = tmp_path / "prompts"
        prompts.mkdir()
        (prompts / "v0.md").write_text("<!-- placeholder -->", encoding="utf-8")
        monkeypatch.setattr(prompt_module, "PROMPTS_DIR", prompts)
        from eval.prompt import PromptError

        with pytest.raises(PromptError):
            Extractor(model="claude-sonnet-4-6", prompt_version="v0", client=mock_client)


# ---------------------------------------------------------------------------
# Message construction
# ---------------------------------------------------------------------------

class TestMessageStructure:
    def test_system_param_has_cache_control_by_default(
        self, real_prompt: Path, mock_client: MagicMock, sample_pdf: Path
    ) -> None:
        e = Extractor(model="claude-sonnet-4-6", prompt_version="v0", client=mock_client)
        e.extract(sample_pdf)
        kwargs = mock_client.messages.create.call_args.kwargs
        system = kwargs["system"]
        assert isinstance(system, list)
        assert system[0]["type"] == "text"
        assert system[0]["cache_control"] == {"type": "ephemeral", "ttl": "5m"}

    def test_no_cache_disables_cache_control(
        self, real_prompt: Path, mock_client: MagicMock, sample_pdf: Path
    ) -> None:
        e = Extractor(
            model="claude-sonnet-4-6",
            prompt_version="v0",
            client=mock_client,
            use_cache=False,
        )
        e.extract(sample_pdf)
        system = mock_client.messages.create.call_args.kwargs["system"]
        assert "cache_control" not in system[0]

    def test_user_message_has_pdf_base64_and_instruction(
        self, real_prompt: Path, mock_client: MagicMock, sample_pdf: Path
    ) -> None:
        e = Extractor(model="claude-sonnet-4-6", prompt_version="v0", client=mock_client)
        e.extract(sample_pdf)
        messages = mock_client.messages.create.call_args.kwargs["messages"]
        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        content = messages[0]["content"]
        assert content[0]["type"] == "document"
        assert content[0]["source"]["media_type"] == "application/pdf"
        # Verify the base64 round-trips back to the original PDF bytes
        decoded = base64.standard_b64decode(content[0]["source"]["data"])
        assert decoded == sample_pdf.read_bytes()
        # The trailing instruction asks for JSON
        assert content[1]["type"] == "text"
        assert "JSON" in content[1]["text"].upper()

    def test_model_and_max_tokens_flow_through(
        self, real_prompt: Path, mock_client: MagicMock, sample_pdf: Path
    ) -> None:
        e = Extractor(
            model="claude-haiku-4-5-20251001",
            prompt_version="v0",
            client=mock_client,
            max_tokens=4096,
        )
        e.extract(sample_pdf)
        kwargs = mock_client.messages.create.call_args.kwargs
        assert kwargs["model"] == "claude-haiku-4-5-20251001"
        assert kwargs["max_tokens"] == 4096
        assert kwargs["temperature"] == 0

    def test_missing_pdf_raises(
        self, real_prompt: Path, mock_client: MagicMock, tmp_path: Path
    ) -> None:
        e = Extractor(model="claude-sonnet-4-6", prompt_version="v0", client=mock_client)
        with pytest.raises(FileNotFoundError):
            e.extract(tmp_path / "does_not_exist.pdf")


# ---------------------------------------------------------------------------
# Response handling
# ---------------------------------------------------------------------------

class TestResponseParsing:
    def test_token_usage_propagated(
        self, real_prompt: Path, mock_client: MagicMock, sample_pdf: Path
    ) -> None:
        e = Extractor(model="claude-sonnet-4-6", prompt_version="v0", client=mock_client)
        result = e.extract(sample_pdf)
        assert result.input_tokens == 1000
        assert result.output_tokens == 500
        assert result.cached_input_tokens == 800

    def test_successful_parse_returns_canonical(
        self, real_prompt: Path, mock_client: MagicMock, sample_pdf: Path
    ) -> None:
        e = Extractor(model="claude-sonnet-4-6", prompt_version="v0", client=mock_client)
        result = e.extract(sample_pdf)
        assert result.canonical is not None
        assert result.parse_error is None
        assert result.canonical.document_number == "TEST-1"

    def test_parse_error_captures_invalid_json(
        self,
        real_prompt: Path,
        mock_client: MagicMock,
        mock_client_response: MagicMock,
        sample_pdf: Path,
    ) -> None:
        mock_client_response.content = [SimpleNamespace(text="not valid json at all")]
        e = Extractor(model="claude-sonnet-4-6", prompt_version="v0", client=mock_client)
        result = e.extract(sample_pdf)
        assert result.canonical is None
        assert result.parse_error is not None

    def test_handles_fenced_json_response(
        self,
        real_prompt: Path,
        mock_client: MagicMock,
        mock_client_response: MagicMock,
        sample_pdf: Path,
    ) -> None:
        body = json.dumps(_valid_canonical_json_dict())
        mock_client_response.content = [
            SimpleNamespace(text=f"Here is the extraction:\n\n```json\n{body}\n```\n")
        ]
        e = Extractor(model="claude-sonnet-4-6", prompt_version="v0", client=mock_client)
        result = e.extract(sample_pdf)
        assert result.canonical is not None

    def test_handles_bare_json_with_leading_prose(
        self,
        real_prompt: Path,
        mock_client: MagicMock,
        mock_client_response: MagicMock,
        sample_pdf: Path,
    ) -> None:
        body = json.dumps(_valid_canonical_json_dict())
        mock_client_response.content = [
            SimpleNamespace(text=f"Sure, here you go: {body}")
        ]
        e = Extractor(model="claude-sonnet-4-6", prompt_version="v0", client=mock_client)
        result = e.extract(sample_pdf)
        assert result.canonical is not None


# ---------------------------------------------------------------------------
# Helper internals
# ---------------------------------------------------------------------------

class TestJsonObjectExtraction:
    def test_extracts_balanced_object(self) -> None:
        assert _extract_first_json_object('prefix {"a": 1} suffix') == '{"a": 1}'

    def test_extracts_nested(self) -> None:
        assert _extract_first_json_object('{"a": {"b": 1}}') == '{"a": {"b": 1}}'

    def test_handles_braces_in_strings(self) -> None:
        """A '}' inside a JSON string must not close the outer object early."""
        assert _extract_first_json_object('{"a": "x{y}"}') == '{"a": "x{y}"}'

    def test_returns_none_when_no_object(self) -> None:
        assert _extract_first_json_object("plain text, no braces") is None

    def test_handles_escaped_quotes(self) -> None:
        raw = '{"a": "he said \\"hi\\""}'
        assert _extract_first_json_object(raw) == raw


class TestTryParseCanonical:
    def test_returns_canonical_for_valid_json(self) -> None:
        body = json.dumps(_valid_canonical_json_dict())
        canonical, err = _try_parse_canonical(body)
        assert canonical is not None
        assert err is None

    def test_returns_error_for_invalid_json(self) -> None:
        canonical, err = _try_parse_canonical("totally not json")
        assert canonical is None
        assert err is not None

    def test_returns_error_for_valid_json_but_wrong_schema(self) -> None:
        canonical, err = _try_parse_canonical('{"this_is_not": "CanonicalInvoice"}')
        assert canonical is None
        assert err is not None
        assert "schema validation" in err.lower() or "field required" in err.lower()

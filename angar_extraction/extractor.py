"""Anthropic SDK wrapper for the eval harness.

Wraps `client.messages.create` with the Angar.ai conventions:

- The PDF is sent as a base64 'document' content block (the SDK's vision /
  PDF input shape, verified against /anthropics/anthropic-sdk-python).
- The system prompt is wrapped in a TextBlockParam with cache_control:
  {"type": "ephemeral", "ttl": "5m"} so a full 18-doc run hits the cache
  on documents 2..18. Cuts cost roughly 5x.
- Temperature is 0 — eval should be as deterministic as the API allows.
- The model is parameterized via __init__ for the --model CLI flag.
- Parse failures are captured in ExtractionResult.parse_error rather than
  raised: a parse failure is a real data point the comparator should still
  score (as all-wrong) instead of an exception that aborts the eval run.
"""

from __future__ import annotations

import base64
import json
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from anthropic import (
    Anthropic,
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    InternalServerError,
    RateLimitError,
)

from angar_extraction.errors import (
    AnthropicAPIError,
    AnthropicAuthError,
    AnthropicOverloadedError,
    AnthropicRateLimitError,
    MalformedPDFError,
)
from angar_schema.canonical import CanonicalInvoice
from angar_extraction.prompt import load_prompt


_EXTRACT_INSTRUCTION = (
    "Extract this document into the Angar.ai CanonicalInvoice schema. "
    "Return ONLY a single JSON object, no surrounding prose. If you must use "
    "a code fence, use ```json. Honest nulls only — never invent fields."
)

_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*\n(.*?)\n```", re.DOTALL)


@dataclass(frozen=True)
class ExtractionResult:
    """Outcome of one extraction attempt against one PDF."""

    canonical: CanonicalInvoice | None       # None if parse / validate failed
    raw_response: str                        # the model's verbatim text output
    input_tokens: int
    cached_input_tokens: int                 # cache_read_input_tokens
    output_tokens: int
    processing_time_ms: int
    parse_error: str | None = None           # human-readable if canonical is None


class Extractor:
    """Thin wrapper around anthropic.Anthropic with prompt caching baked in.

    Construct once per eval run (so the system prompt is loaded once); call
    .extract(pdf_path) per document. The Anthropic client is created lazily
    if not injected, so tests can pass a mock.
    """

    def __init__(
        self,
        *,
        model: str,
        prompt_version: str,
        use_cache: bool = True,
        max_tokens: int = 8192,
        client: Anthropic | None = None,
    ) -> None:
        self.model = model
        self.prompt_version = prompt_version
        self.use_cache = use_cache
        self.max_tokens = max_tokens
        self.system_prompt = load_prompt(prompt_version)
        self._client = client  # lazy: see .client property

    @property
    def client(self) -> Anthropic:
        if self._client is None:
            self._client = Anthropic()  # reads ANTHROPIC_API_KEY from env
        return self._client

    def extract(self, pdf_path: Path) -> ExtractionResult:
        if not pdf_path.is_file():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        pdf_b64 = base64.standard_b64encode(pdf_path.read_bytes()).decode("ascii")
        system_param = self._build_system_param()
        messages = self._build_messages(pdf_b64)

        started = time.perf_counter()
        message = self._call_with_retry(system_param, messages)
        elapsed_ms = int((time.perf_counter() - started) * 1000)

        raw = _join_text_blocks(message.content)
        canonical, parse_error = _try_parse_canonical(raw)

        return ExtractionResult(
            canonical=canonical,
            raw_response=raw,
            input_tokens=getattr(message.usage, "input_tokens", 0) or 0,
            cached_input_tokens=(
                getattr(message.usage, "cache_read_input_tokens", 0) or 0
            ),
            output_tokens=getattr(message.usage, "output_tokens", 0) or 0,
            processing_time_ms=elapsed_ms,
            parse_error=parse_error,
        )

    # ---- internals ----

    _MAX_RETRIES = 3
    _RETRY_BASE_SECONDS = 2.0

    def _call_with_retry(
        self,
        system_param: list[dict[str, Any]],
        messages: list[dict[str, Any]],
    ) -> Any:
        """Wrap `client.messages.create` with typed-exception translation and
        exponential backoff on the transient SDK errors (rate-limit, overloaded,
        timeout, connection). Non-transient SDK errors re-raise immediately as
        our typed exceptions.
        """
        last_transient: Exception | None = None
        for attempt in range(self._MAX_RETRIES):
            try:
                return self.client.messages.create(
                    model=self.model,
                    max_tokens=self.max_tokens,
                    temperature=0,
                    system=system_param,
                    messages=messages,
                )
            except AuthenticationError as exc:
                raise AnthropicAuthError(str(exc)) from exc
            except BadRequestError as exc:
                raise MalformedPDFError(str(exc)) from exc
            except RateLimitError as exc:
                last_transient = exc
                wrapped: Exception = AnthropicRateLimitError(str(exc))
            except InternalServerError as exc:
                last_transient = exc
                # 529 = overloaded; other 5xx = generic upstream failure.
                status = getattr(exc, "status_code", None)
                wrapped = (
                    AnthropicOverloadedError(str(exc))
                    if status == 529
                    else AnthropicAPIError(str(exc))
                )
            except (APIConnectionError, APITimeoutError) as exc:
                last_transient = exc
                wrapped = AnthropicAPIError(str(exc))
            except APIStatusError as exc:
                # Status-coded but not one of the specific subclasses above.
                status = getattr(exc, "status_code", None)
                if status == 529:
                    last_transient = exc
                    wrapped = AnthropicOverloadedError(str(exc))
                elif status and 500 <= status < 600:
                    last_transient = exc
                    wrapped = AnthropicAPIError(str(exc))
                else:
                    raise AnthropicAPIError(str(exc)) from exc

            if attempt + 1 == self._MAX_RETRIES:
                raise wrapped from last_transient
            time.sleep(self._RETRY_BASE_SECONDS * (2**attempt))
        # Unreachable: loop returns or raises.
        raise AnthropicAPIError("retry loop exhausted with no result")

    def _build_system_param(self) -> list[dict[str, Any]]:
        block: dict[str, Any] = {"type": "text", "text": self.system_prompt}
        if self.use_cache:
            block["cache_control"] = {"type": "ephemeral", "ttl": "5m"}
        return [block]

    def _build_messages(self, pdf_b64: str) -> list[dict[str, Any]]:
        return [
            {
                "role": "user",
                "content": [
                    {
                        "type": "document",
                        "source": {
                            "type": "base64",
                            "data": pdf_b64,
                            "media_type": "application/pdf",
                        },
                    },
                    {"type": "text", "text": _EXTRACT_INSTRUCTION},
                ],
            }
        ]


# ---------------------------------------------------------------------------
# Response parsing
# ---------------------------------------------------------------------------

def _join_text_blocks(content: list[Any]) -> str:
    """Concatenate the .text attribute of every TextBlock in the response."""
    parts: list[str] = []
    for block in content:
        text = getattr(block, "text", None)
        if text:
            parts.append(text)
    return "\n".join(parts)


def _try_parse_canonical(
    raw_text: str,
) -> tuple[CanonicalInvoice | None, str | None]:
    """Extract a JSON object from the response and validate it.

    Tries (in order): a ```json``` or bare ``` fenced block, then the whole
    response stripped of leading prose. Captures the failure reason instead
    of raising — a parse failure is a real eval signal, not an abort.
    """
    candidates: list[str] = []
    fence = _JSON_FENCE_RE.search(raw_text)
    if fence:
        candidates.append(fence.group(1))
    # Fallback: take the first {...} balanced span. Most prompts that say
    # "JSON only" produce a bare JSON object with no fence.
    bare = _extract_first_json_object(raw_text)
    if bare:
        candidates.append(bare)
    if not candidates:
        return None, "no JSON object found in response"

    last_error: str | None = None
    for candidate in candidates:
        try:
            data = json.loads(candidate)
        except json.JSONDecodeError as exc:
            last_error = f"json decode: {exc}"
            continue
        try:
            return CanonicalInvoice.model_validate(data), None
        except Exception as exc:
            last_error = f"schema validation: {exc}"
    return None, last_error


def _extract_first_json_object(text: str) -> str | None:
    """Return the substring of the first balanced {...} JSON object, or None."""
    start = text.find("{")
    if start == -1:
        return None
    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return None

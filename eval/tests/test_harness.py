"""Smoke tests for eval.harness CLI.

End-to-end with a mocked Extractor — no Anthropic API calls. Verifies:
- Argument parsing
- Missing API key returns 1
- Successful run returns 0 and writes a results JSON
- --compare-to with regression returns 2
- --compare-to with improvement returns 0
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from eval import canonical_path  # noqa: F401
from canonical import (  # noqa: E402
    CanonicalInvoice,
    Currency,
    DocumentType,
    ExtractionMetadata,
)
from eval import harness
from eval.extractor import ExtractionResult


# ---------------------------------------------------------------------------
# Helpers: build a self-contained foundation dir (pdfs + labels)
# ---------------------------------------------------------------------------

_MINIMAL_LABEL = """# Synthetic label

```json
{
  "accepted": true,
  "document_type": "regular_invoice",
  "document_number": "TEST-1",
  "document_date": "2026-01-01",
  "document_currency": "GEL",
  "items": [],
  "extraction": {
    "source_filename": "synthetic.pdf",
    "source_pdf_sha256": "abc",
    "extracted_at": "2026-01-01T00:00:00Z",
    "model_version": "test",
    "prompt_version": "test"
  }
}
```
"""


@pytest.fixture
def fake_foundation(tmp_path: Path) -> Path:
    foundation = tmp_path / "foundation"
    pdfs = foundation / "pdfs"
    labels = foundation / "labels"
    pdfs.mkdir(parents=True)
    labels.mkdir(parents=True)
    (pdfs / "invoice_001.pdf").write_bytes(b"%PDF-1.4 fake")
    (labels / "invoice_001.md").write_text(_MINIMAL_LABEL, encoding="utf-8")
    return foundation


@pytest.fixture
def fake_runs_dir(tmp_path: Path) -> Path:
    return tmp_path / "runs"


@pytest.fixture
def fake_prompt(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    prompts = tmp_path / "prompts"
    prompts.mkdir()
    (prompts / "v0.md").write_text("You extract invoices.", encoding="utf-8")
    from eval import prompt as prompt_module
    monkeypatch.setattr(prompt_module, "PROMPTS_DIR", prompts)
    return prompts


@pytest.fixture
def api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-not-real")


def _make_perfect_extraction(name: str = "TEST-1") -> ExtractionResult:
    canonical = CanonicalInvoice(
        accepted=True,
        document_type=DocumentType.REGULAR_INVOICE,
        document_number=name,
        document_currency=Currency.GEL,
        extraction=ExtractionMetadata(
            source_filename="synthetic.pdf",
            source_pdf_sha256="abc",
            extracted_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            model_version="test",
            prompt_version="test",
        ),
    )
    canonical.document_date = __import__("datetime").date(2026, 1, 1)
    return ExtractionResult(
        canonical=canonical,
        raw_response="{}",
        input_tokens=1000,
        cached_input_tokens=800,
        output_tokens=200,
        processing_time_ms=1234,
        parse_error=None,
    )


def _make_failing_extraction() -> ExtractionResult:
    """Simulates a wrong document_number — strict miss, ~80% accuracy."""
    canonical = CanonicalInvoice(
        accepted=True,
        document_type=DocumentType.REGULAR_INVOICE,
        document_number="DIFFERENT",  # mismatch
        document_currency=Currency.GEL,
        extraction=ExtractionMetadata(
            source_filename="synthetic.pdf",
            source_pdf_sha256="abc",
            extracted_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            model_version="test",
            prompt_version="test",
        ),
    )
    canonical.document_date = __import__("datetime").date(2026, 1, 1)
    return ExtractionResult(
        canonical=canonical,
        raw_response="{}",
        input_tokens=1000,
        cached_input_tokens=800,
        output_tokens=200,
        processing_time_ms=1234,
        parse_error=None,
    )


# ---------------------------------------------------------------------------
# Pre-flight checks
# ---------------------------------------------------------------------------

class TestPreflightChecks:
    def test_missing_api_key_exits_1(
        self,
        monkeypatch: pytest.MonkeyPatch,
        fake_foundation: Path,
        fake_runs_dir: Path,
        fake_prompt: Path,
    ) -> None:
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        # Also ensure load_dotenv doesn't pick one up
        monkeypatch.setattr(harness, "load_dotenv", lambda *a, **k: None)
        code = harness.main([
            "--foundation", str(fake_foundation),
            "--runs-dir", str(fake_runs_dir),
        ])
        assert code == 1

    def test_missing_fixture_exits_1(
        self, api_key: None, fake_foundation: Path, fake_runs_dir: Path, fake_prompt: Path
    ) -> None:
        code = harness.main([
            "--doc", "nonexistent",
            "--foundation", str(fake_foundation),
            "--runs-dir", str(fake_runs_dir),
        ])
        assert code == 1


# ---------------------------------------------------------------------------
# End-to-end with mocked Extractor
# ---------------------------------------------------------------------------

class TestEndToEnd:
    def test_perfect_run_exits_0_and_writes_results(
        self,
        api_key: None,
        fake_foundation: Path,
        fake_runs_dir: Path,
        fake_prompt: Path,
    ) -> None:
        with patch.object(harness, "Extractor") as mock_extractor_cls:
            mock_instance = MagicMock()
            mock_instance.extract.return_value = _make_perfect_extraction()
            mock_extractor_cls.return_value = mock_instance

            code = harness.main([
                "--foundation", str(fake_foundation),
                "--runs-dir", str(fake_runs_dir),
            ])

        assert code == 0
        # A JSON file should have been persisted
        runs = list(fake_runs_dir.glob("*.json"))
        assert len(runs) == 1
        data = json.loads(runs[0].read_text(encoding="utf-8"))
        assert data["overall_accuracy"] == 1.0

    def test_compare_to_with_regression_exits_2(
        self,
        api_key: None,
        fake_foundation: Path,
        fake_runs_dir: Path,
        fake_prompt: Path,
    ) -> None:
        # First, persist a 100% baseline using a perfect extraction
        with patch.object(harness, "Extractor") as mock_cls:
            mock_inst = MagicMock()
            mock_inst.extract.return_value = _make_perfect_extraction()
            mock_cls.return_value = mock_inst
            assert harness.main([
                "--foundation", str(fake_foundation),
                "--runs-dir", str(fake_runs_dir),
            ]) == 0
        baseline_path = next(fake_runs_dir.glob("*.json"))

        # Now run again with a failing extraction → regression
        with patch.object(harness, "Extractor") as mock_cls:
            mock_inst = MagicMock()
            mock_inst.extract.return_value = _make_failing_extraction()
            mock_cls.return_value = mock_inst
            code = harness.main([
                "--foundation", str(fake_foundation),
                "--runs-dir", str(fake_runs_dir),
                "--compare-to", str(baseline_path),
                "--gate", "0.02",
            ])
        assert code == 2

    def test_compare_to_with_improvement_exits_0(
        self,
        api_key: None,
        fake_foundation: Path,
        fake_runs_dir: Path,
        fake_prompt: Path,
    ) -> None:
        # Baseline: a failing extraction
        with patch.object(harness, "Extractor") as mock_cls:
            mock_inst = MagicMock()
            mock_inst.extract.return_value = _make_failing_extraction()
            mock_cls.return_value = mock_inst
            assert harness.main([
                "--foundation", str(fake_foundation),
                "--runs-dir", str(fake_runs_dir),
            ]) == 0
        baseline_path = next(fake_runs_dir.glob("*.json"))

        # Current: a perfect extraction → improvement, no regression
        with patch.object(harness, "Extractor") as mock_cls:
            mock_inst = MagicMock()
            mock_inst.extract.return_value = _make_perfect_extraction()
            mock_cls.return_value = mock_inst
            code = harness.main([
                "--foundation", str(fake_foundation),
                "--runs-dir", str(fake_runs_dir),
                "--compare-to", str(baseline_path),
                "--gate", "0.02",
            ])
        assert code == 0


# ---------------------------------------------------------------------------
# Arg parser
# ---------------------------------------------------------------------------

class TestArgParser:
    def test_defaults(self) -> None:
        parser = harness._build_arg_parser()
        args = parser.parse_args([])
        assert args.model == "claude-sonnet-4-6"
        assert args.prompt_version == "v0"
        assert args.no_cache is False
        assert args.gate == 0.02

    def test_no_cache_flag(self) -> None:
        args = harness._build_arg_parser().parse_args(["--no-cache"])
        assert args.no_cache is True

    def test_custom_model(self) -> None:
        args = harness._build_arg_parser().parse_args(
            ["--model", "claude-haiku-4-5-20251001"]
        )
        assert args.model == "claude-haiku-4-5-20251001"

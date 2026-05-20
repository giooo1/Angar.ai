"""Unit tests for eval.fixtures.

No Anthropic API calls. Synthetic markdown + minimal CanonicalInvoice JSON
written into pytest tmp_path. These tests verify the fixture loader's
contract: it pairs PDFs with labels, parses the JSON block, validates
against the schema, and fails loudly when any of those go wrong.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from eval.fixtures import (
    Fixture,
    FixtureError,
    _extract_json_block,
    load_fixtures,
    load_single,
)


# ---------------------------------------------------------------------------
# Helpers: build a minimal valid CanonicalInvoice JSON for use as a label body
# ---------------------------------------------------------------------------

def _minimal_canonical_dict() -> dict:
    """Smallest possible CanonicalInvoice that validates."""
    return {
        "accepted": True,
        "rejection_reason": None,
        "document_type": "regular_invoice",
        "document_number": "TEST-1",
        "document_date": "2026-01-01",
        "document_currency": "GEL",
        "seller": None,
        "buyer": None,
        "items": [],
        "subtotal_total": None,
        "vat_total": None,
        "discount_total": None,
        "shipping_cost": None,
        "grand_total": None,
        "is_vat_invoice": False,
        "is_reverse_vat": False,
        "vat_treatment_overall": "unknown",
        "vat_treatment_reason": None,
        "is_free_of_charge": False,
        "references_other_document": None,
        "transport": None,
        "notes": None,
        "contains_pii_beyond_parties": False,
        "extraction_notes": [],
        "extraction": {
            "source_filename": "synthetic.pdf",
            "source_pdf_sha256": "deadbeef",
            "extracted_at": "2026-01-01T00:00:00Z",
            "model_version": "test",
            "prompt_version": "test",
            "field_confidence": {},
            "warnings": [],
            "processing_time_ms": None,
        },
    }


def _label_md(canonical: dict, header: str = "# Gold label") -> str:
    return f"{header}\n\nSome prose.\n\n```json\n{json.dumps(canonical, indent=2)}\n```\n"


def _make_pair(foundation: Path, name: str, canonical: dict | None = None) -> tuple[Path, Path]:
    """Drop a (pdf, label) pair under foundation/{pdfs,labels}/. Returns (pdf, label)."""
    pdfs = foundation / "pdfs"
    labels = foundation / "labels"
    pdfs.mkdir(parents=True, exist_ok=True)
    labels.mkdir(parents=True, exist_ok=True)
    pdf = pdfs / f"{name}.pdf"
    label = labels / f"{name}.md"
    pdf.write_bytes(b"%PDF-1.4 fake")
    label.write_text(_label_md(canonical or _minimal_canonical_dict()), encoding="utf-8")
    return pdf, label


# ---------------------------------------------------------------------------
# _extract_json_block
# ---------------------------------------------------------------------------

class TestExtractJsonBlock:
    def test_extracts_block_after_markdown_header(self, tmp_path: Path) -> None:
        md = "# A title\n\nsome prose\n\n```json\n{\"x\": 1}\n```\n"
        result = _extract_json_block(md, tmp_path / "fake.md")
        assert result == '{"x": 1}'

    def test_extracts_first_block_when_multiple(self, tmp_path: Path) -> None:
        md = "```json\n{\"first\": 1}\n```\n\nthen\n\n```json\n{\"second\": 2}\n```\n"
        result = _extract_json_block(md, tmp_path / "fake.md")
        assert result == '{"first": 1}'

    def test_raises_when_no_json_block(self, tmp_path: Path) -> None:
        md = "# Just prose, no code fence anywhere\n"
        with pytest.raises(FixtureError, match="No ```json``` fenced block"):
            _extract_json_block(md, tmp_path / "fake.md")

    def test_raises_when_only_non_json_fence(self, tmp_path: Path) -> None:
        md = "```python\nprint('hi')\n```\n"
        with pytest.raises(FixtureError, match="No ```json``` fenced block"):
            _extract_json_block(md, tmp_path / "fake.md")

    def test_includes_source_path_in_error(self, tmp_path: Path) -> None:
        source = tmp_path / "labels" / "missing.md"
        with pytest.raises(FixtureError, match=str(source).replace("\\", r"\\")):
            _extract_json_block("no json here", source)


# ---------------------------------------------------------------------------
# load_single
# ---------------------------------------------------------------------------

class TestLoadSingle:
    def test_loads_valid_pair(self, tmp_path: Path) -> None:
        _make_pair(tmp_path, "invoice_001")
        fixture = load_single(tmp_path, "invoice_001")
        assert isinstance(fixture, Fixture)
        assert fixture.name == "invoice_001"
        assert fixture.pdf_path.name == "invoice_001.pdf"
        assert fixture.label_path.name == "invoice_001.md"
        assert fixture.ground_truth.document_number == "TEST-1"

    def test_raises_when_pdf_missing(self, tmp_path: Path) -> None:
        _make_pair(tmp_path, "invoice_001")
        (tmp_path / "pdfs" / "invoice_001.pdf").unlink()
        with pytest.raises(FixtureError, match="PDF not found"):
            load_single(tmp_path, "invoice_001")

    def test_raises_when_label_missing(self, tmp_path: Path) -> None:
        _make_pair(tmp_path, "invoice_001")
        (tmp_path / "labels" / "invoice_001.md").unlink()
        with pytest.raises(FixtureError, match="Label not found"):
            load_single(tmp_path, "invoice_001")

    def test_raises_on_invalid_json(self, tmp_path: Path) -> None:
        _make_pair(tmp_path, "invoice_001")
        bad_md = "```json\n{this is not valid json\n```\n"
        (tmp_path / "labels" / "invoice_001.md").write_text(bad_md, encoding="utf-8")
        with pytest.raises(FixtureError, match="Invalid JSON"):
            load_single(tmp_path, "invoice_001")

    def test_raises_on_schema_mismatch(self, tmp_path: Path) -> None:
        canonical = _minimal_canonical_dict()
        canonical["document_type"] = "not_a_real_enum_value"
        _make_pair(tmp_path, "invoice_001", canonical=canonical)
        with pytest.raises(FixtureError, match="does not match CanonicalInvoice schema"):
            load_single(tmp_path, "invoice_001")


# ---------------------------------------------------------------------------
# load_fixtures
# ---------------------------------------------------------------------------

class TestLoadFixtures:
    def test_loads_all_pairs_sorted_by_name(self, tmp_path: Path) -> None:
        _make_pair(tmp_path, "invoice_002")
        _make_pair(tmp_path, "invoice_001")
        _make_pair(tmp_path, "Waybill_List1")
        fixtures = load_fixtures(tmp_path)
        assert [f.name for f in fixtures] == ["Waybill_List1", "invoice_001", "invoice_002"]

    def test_raises_when_pdfs_dir_missing(self, tmp_path: Path) -> None:
        (tmp_path / "labels").mkdir()
        with pytest.raises(FixtureError, match="PDFs directory not found"):
            load_fixtures(tmp_path)

    def test_raises_when_labels_dir_missing(self, tmp_path: Path) -> None:
        (tmp_path / "pdfs").mkdir()
        with pytest.raises(FixtureError, match="Labels directory not found"):
            load_fixtures(tmp_path)

    def test_raises_on_orphan_pdf(self, tmp_path: Path) -> None:
        _make_pair(tmp_path, "invoice_001")
        (tmp_path / "pdfs" / "orphan.pdf").write_bytes(b"%PDF")
        with pytest.raises(FixtureError, match="PDFs without labels"):
            load_fixtures(tmp_path)

    def test_raises_on_orphan_label(self, tmp_path: Path) -> None:
        _make_pair(tmp_path, "invoice_001")
        (tmp_path / "labels" / "orphan.md").write_text(
            _label_md(_minimal_canonical_dict()), encoding="utf-8"
        )
        with pytest.raises(FixtureError, match="Labels without PDFs"):
            load_fixtures(tmp_path)

    def test_empty_dirs_returns_empty_list(self, tmp_path: Path) -> None:
        (tmp_path / "pdfs").mkdir()
        (tmp_path / "labels").mkdir()
        assert load_fixtures(tmp_path) == []


# ---------------------------------------------------------------------------
# Integration with the real foundation folder (skipped if not present)
# ---------------------------------------------------------------------------

class TestRealFoundation:
    """One slow test that loads the actual 18-doc foundation set.

    Skipped if the foundation folder isn't present (e.g. CI on a thin checkout).
    """

    @pytest.fixture
    def foundation_dir(self) -> Path:
        # eval/tests/test_fixtures.py -> eval/tests -> eval -> repo root
        root = Path(__file__).resolve().parents[2]
        foundation = root / "project foundation"
        if not foundation.is_dir():
            pytest.skip(f"foundation dir not found at {foundation}")
        return foundation

    def test_loads_all_18_real_labels(self, foundation_dir: Path) -> None:
        fixtures = load_fixtures(foundation_dir)
        assert len(fixtures) == 18
        # Every fixture's ground_truth should be a valid CanonicalInvoice
        for f in fixtures:
            assert f.ground_truth.document_type is not None
            assert f.pdf_path.exists()
            assert f.label_path.exists()

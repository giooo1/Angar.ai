"""Load hand-labeled fixtures from `project foundation/` for eval runs.

A fixture is a (PDF, label) pair sharing a basename. The label is a Markdown
file with a single fenced ```json block that deserializes into a
CanonicalInvoice. The PDF is what we feed to Claude vision.

Loud failures over silent ones: orphan PDFs, orphan labels, malformed JSON,
and schema mismatches all raise FixtureError with the source file path.
That's the eval set's contract: every doc has a paired, valid label.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from angar_schema.canonical import CanonicalInvoice

_JSON_BLOCK_RE = re.compile(r"```json\s*\n(.*?)\n```", re.DOTALL)


class FixtureError(Exception):
    """A fixture could not be loaded. Always raised with a file-path hint."""


@dataclass(frozen=True)
class Fixture:
    """A single eval fixture: a PDF + its hand-labeled ground truth."""

    name: str
    pdf_path: Path
    label_path: Path
    ground_truth: CanonicalInvoice


def load_fixtures(foundation_dir: Path) -> list[Fixture]:
    """Load every (PDF, label) pair under `foundation_dir`.

    Pairs by basename: `pdfs/invoice_001.pdf` ↔ `labels/invoice_001.md`.
    Raises FixtureError on orphans either direction, missing JSON blocks,
    invalid JSON, or schema-validation failure.
    """
    pdfs_dir = foundation_dir / "pdfs"
    labels_dir = foundation_dir / "labels"

    if not pdfs_dir.is_dir():
        raise FixtureError(f"PDFs directory not found: {pdfs_dir}")
    if not labels_dir.is_dir():
        raise FixtureError(f"Labels directory not found: {labels_dir}")

    pdf_paths = {p.stem: p for p in pdfs_dir.glob("*.pdf")}
    label_paths = {p.stem: p for p in labels_dir.glob("*.md")}

    pdf_names = set(pdf_paths)
    label_names = set(label_paths)

    orphan_pdfs = sorted(pdf_names - label_names)
    if orphan_pdfs:
        raise FixtureError(
            f"PDFs without labels (basenames): {orphan_pdfs}. "
            f"Every PDF must have a matching .md label in {labels_dir}."
        )

    orphan_labels = sorted(label_names - pdf_names)
    if orphan_labels:
        raise FixtureError(
            f"Labels without PDFs (basenames): {orphan_labels}. "
            f"Every .md label must have a matching .pdf in {pdfs_dir}."
        )

    return [
        _build_fixture(name, pdf_paths[name], label_paths[name])
        for name in sorted(pdf_names)
    ]


def load_single(foundation_dir: Path, name: str) -> Fixture:
    """Load one fixture by basename (e.g. 'invoice_001' or 'Waybill_List1').

    Raises FixtureError if either side is missing.
    """
    pdf_path = foundation_dir / "pdfs" / f"{name}.pdf"
    label_path = foundation_dir / "labels" / f"{name}.md"

    if not pdf_path.is_file():
        raise FixtureError(f"PDF not found: {pdf_path}")
    if not label_path.is_file():
        raise FixtureError(f"Label not found: {label_path}")

    return _build_fixture(name, pdf_path, label_path)


def _build_fixture(name: str, pdf_path: Path, label_path: Path) -> Fixture:
    md_text = label_path.read_text(encoding="utf-8")
    json_text = _extract_json_block(md_text, label_path)
    ground_truth = _parse_and_validate(json_text, label_path)
    return Fixture(
        name=name,
        pdf_path=pdf_path,
        label_path=label_path,
        ground_truth=ground_truth,
    )


def _extract_json_block(md_text: str, source: Path) -> str:
    """Pull the first ```json ... ``` fenced block from a markdown file."""
    match = _JSON_BLOCK_RE.search(md_text)
    if match is None:
        raise FixtureError(
            f"No ```json``` fenced block found in {source}. "
            f"Labels must contain exactly one JSON code block conforming to "
            f"CanonicalInvoice."
        )
    return match.group(1)


def _parse_and_validate(json_text: str, source: Path) -> CanonicalInvoice:
    try:
        data = json.loads(json_text)
    except json.JSONDecodeError as exc:
        raise FixtureError(
            f"Invalid JSON in {source} at line {exc.lineno} col {exc.colno}: {exc.msg}"
        ) from exc

    try:
        return CanonicalInvoice.model_validate(data)
    except Exception as exc:
        raise FixtureError(
            f"Label JSON in {source} does not match CanonicalInvoice schema: {exc}"
        ) from exc

"""Field-by-field comparator for eval runs.

Implements Phase 3 §5.2 three-tier scoring exactly:

  Strict    (weight 0.90)  exact match required (TINs, dates, Money amounts, flags)
  Semantic  (weight 0.60)  exact OR fuzzy match (Jaccard >= 0.85 for names/items;
                                                  >= 0.70 for addresses)
  Free-text (weight 0.30)  topic coverage on key tokens (extraction_notes,
                                                          vat_treatment_reason,
                                                          rejection_reason)

Overall accuracy = sum(weight * score) / sum(weight) across all fields.

Per the Phase 3 spec, the comparator does not re-implement extraction rules.
It only normalizes whitespace and case for string compares. Family-specific
rules (DRESSUP strips '#', invoice 0496-style preserves bare numbers, etc.)
are the prompt's responsibility — if the prompt outputs the wrong form, the
strict-match will catch it. That's what eval is for.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Literal

from angar_schema.canonical import (
    CanonicalInvoice,
    LineItem,
    Money,
    Party,
    TransportInfo,
)

Tier = Literal["strict", "semantic", "free_text"]

# Phase 3 §5.2 weights
TIER_WEIGHT: dict[Tier, float] = {
    "strict": 0.90,
    "semantic": 0.60,
    "free_text": 0.30,
}

# Phase 3 §5.2 thresholds
NAME_DESC_JACCARD_THRESHOLD = 0.85
ADDRESS_JACCARD_THRESHOLD = 0.70

# English + Georgian stopwords for free-text topic coverage. Kept small and
# generic on purpose — domain vocabulary should be the basis for coverage
# scoring, not function words.
_STOPWORDS = frozenset(
    {
        # English
        "a", "an", "the", "is", "are", "was", "were", "be", "been", "of", "in",
        "on", "to", "for", "and", "or", "but", "as", "at", "by", "from", "with",
        "this", "that", "these", "those", "it", "its", "not", "no", "do", "does",
        # Georgian common function words (limited; expand if topic-coverage tests fail)
        "და", "ან", "მაგრამ", "თუ", "რომ", "არის", "იყო",
    }
)


# ---------------------------------------------------------------------------
# Public data shapes
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class FieldResult:
    """Outcome of comparing one field between expected and actual."""
    path: str
    tier: Tier
    expected: Any        # serializable for JSON persistence (str/None/etc.)
    actual: Any
    correct: bool        # True iff score == 1.0 (or, for tiered semantic, above threshold)
    score: float         # 0.0–1.0
    note: str | None = None


@dataclass(frozen=True)
class DocResult:
    """Outcome of comparing one document's expected vs actual extraction."""
    fixture_name: str
    fields: list[FieldResult]
    weighted_accuracy: float
    parse_error: str | None = None
    extraction_input_tokens: int = 0
    extraction_cached_input_tokens: int = 0
    extraction_output_tokens: int = 0
    extraction_time_ms: int = 0


# ---------------------------------------------------------------------------
# Top-level entry point
# ---------------------------------------------------------------------------

def compare(
    expected: CanonicalInvoice,
    actual: CanonicalInvoice | None,
    fixture_name: str = "unnamed",
    parse_error: str | None = None,
    extraction_input_tokens: int = 0,
    extraction_cached_input_tokens: int = 0,
    extraction_output_tokens: int = 0,
    extraction_time_ms: int = 0,
) -> DocResult:
    """Compare an expected CanonicalInvoice to an actual extraction.

    If actual is None (the extractor failed to parse a CanonicalInvoice from
    the model response), every scoreable field gets score 0.0 — a parse
    failure is treated as wrong on everything, not as "ignore this run".
    """
    if actual is None:
        fields = _all_zero_fields(expected, parse_error or "no actual extraction")
    elif not expected.accepted:
        # Payment orders and the like: only the rejection-relevant fields are scored.
        fields = _score_rejection(expected, actual)
    else:
        fields = _score_full(expected, actual)

    return DocResult(
        fixture_name=fixture_name,
        fields=fields,
        weighted_accuracy=_weighted_accuracy(fields),
        parse_error=parse_error,
        extraction_input_tokens=extraction_input_tokens,
        extraction_cached_input_tokens=extraction_cached_input_tokens,
        extraction_output_tokens=extraction_output_tokens,
        extraction_time_ms=extraction_time_ms,
    )


def _weighted_accuracy(fields: list[FieldResult]) -> float:
    if not fields:
        return 0.0
    num = 0.0
    den = 0.0
    for f in fields:
        w = TIER_WEIGHT[f.tier]
        num += w * f.score
        den += w
    return num / den if den > 0 else 0.0


# ---------------------------------------------------------------------------
# Full-document scoring (accepted=true case)
# ---------------------------------------------------------------------------

def _score_full(e: CanonicalInvoice, a: CanonicalInvoice) -> list[FieldResult]:
    out: list[FieldResult] = []
    out.extend(_score_doc_identity(e, a))
    out.extend(_score_flags(e, a))
    out.extend(_score_party(e.seller, a.seller, "seller"))
    out.extend(_score_party(e.buyer, a.buyer, "buyer"))
    out.extend(_score_items(e.items, a.items))
    out.extend(_score_totals(e, a))
    out.extend(_score_transport(e.transport, a.transport))
    out.extend(_score_free_text(e, a))
    out.extend(_score_references(e, a))
    return out


def _score_rejection(e: CanonicalInvoice, a: CanonicalInvoice) -> list[FieldResult]:
    """For rejected docs (payment orders, etc.) only certain fields are meaningful.

    Per the spec, rejected docs have seller=None, buyer=None, items=[]. So we
    score: accepted, document_type, document_number, rejection_reason,
    references_other_document, grand_total.
    """
    out: list[FieldResult] = []
    out.append(_strict_equal("accepted", e.accepted, a.accepted))
    out.append(_strict_equal("document_type", e.document_type, a.document_type))
    out.append(_doc_number("document_number", e.document_number, a.document_number))
    out.append(_strict_equal(
        "references_other_document",
        e.references_other_document,
        a.references_other_document,
    ))
    out.extend(_money_field("grand_total", e.grand_total, a.grand_total))
    out.extend(_score_free_text_field(
        "rejection_reason", e.rejection_reason, a.rejection_reason
    ))
    return out


# ---------------------------------------------------------------------------
# Document identity, flags, totals
# ---------------------------------------------------------------------------

def _score_doc_identity(e: CanonicalInvoice, a: CanonicalInvoice) -> list[FieldResult]:
    return [
        _strict_equal("accepted", e.accepted, a.accepted),
        _strict_equal("document_type", e.document_type, a.document_type),
        _doc_number("document_number", e.document_number, a.document_number),
        _strict_equal("document_date", e.document_date, a.document_date),
        _strict_equal("document_currency", e.document_currency, a.document_currency),
    ]


def _score_flags(e: CanonicalInvoice, a: CanonicalInvoice) -> list[FieldResult]:
    return [
        _strict_equal("is_vat_invoice", e.is_vat_invoice, a.is_vat_invoice),
        _strict_equal("is_reverse_vat", e.is_reverse_vat, a.is_reverse_vat),
        _strict_equal("is_free_of_charge", e.is_free_of_charge, a.is_free_of_charge),
        _strict_equal(
            "contains_pii_beyond_parties",
            e.contains_pii_beyond_parties,
            a.contains_pii_beyond_parties,
        ),
        _strict_equal(
            "vat_treatment_overall", e.vat_treatment_overall, a.vat_treatment_overall
        ),
    ]


def _score_totals(e: CanonicalInvoice, a: CanonicalInvoice) -> list[FieldResult]:
    out: list[FieldResult] = []
    out.extend(_money_field("subtotal_total", e.subtotal_total, a.subtotal_total))
    out.extend(_money_field("vat_total", e.vat_total, a.vat_total))
    out.extend(_money_field("discount_total", e.discount_total, a.discount_total))
    out.extend(_money_field("shipping_cost", e.shipping_cost, a.shipping_cost))
    out.extend(_money_field("grand_total", e.grand_total, a.grand_total))
    return out


def _score_references(e: CanonicalInvoice, a: CanonicalInvoice) -> list[FieldResult]:
    return [
        _strict_equal(
            "references_other_document",
            e.references_other_document,
            a.references_other_document,
        ),
    ]


# ---------------------------------------------------------------------------
# Party scoring (seller, buyer)
# ---------------------------------------------------------------------------

def _score_party(
    e: Party | None, a: Party | None, prefix: str
) -> list[FieldResult]:
    out: list[FieldResult] = []
    if e is None and a is None:
        out.append(_pass(f"{prefix}", "strict", None, None, "both None"))
        return out
    if e is None or a is None:
        out.append(_fail(f"{prefix}", "strict", e, a, "presence mismatch"))
        return out

    # Strict-tier sub-fields
    out.append(_tin_field(f"{prefix}.tin", e.tin, a.tin))
    out.append(_strict_equal(
        f"{prefix}.tin_label_present", e.tin_label_present, a.tin_label_present
    ))
    out.append(_strict_equal(f"{prefix}.party_type", e.party_type, a.party_type))
    out.append(_strict_equal(f"{prefix}.script", e.script, a.script))
    # Bank account: strict after whitespace strip
    out.append(_strict_equal(
        f"{prefix}.bank_account",
        _strip_or_none(e.bank_account),
        _strip_or_none(a.bank_account),
    ))

    # Semantic-tier sub-fields
    out.append(_semantic_text(
        f"{prefix}.name", e.name, a.name, NAME_DESC_JACCARD_THRESHOLD
    ))
    out.append(_semantic_text(
        f"{prefix}.address", e.address, a.address, ADDRESS_JACCARD_THRESHOLD
    ))
    return out


# ---------------------------------------------------------------------------
# Line items
# ---------------------------------------------------------------------------

def _score_items(
    expected_items: list[LineItem], actual_items: list[LineItem]
) -> list[FieldResult]:
    out: list[FieldResult] = []

    # 1) Item count (strict): a length mismatch matters per the spec —
    # waybills must not deduplicate, every printed line is one item.
    if len(expected_items) == len(actual_items):
        out.append(_pass(
            "items.count", "strict", len(expected_items), len(actual_items),
            "item count matches",
        ))
    else:
        out.append(_fail(
            "items.count", "strict", len(expected_items), len(actual_items),
            f"expected {len(expected_items)} items, got {len(actual_items)}",
        ))

    # 2) Per-item scoring at shared positions. Missing/extra items score 0.
    paired = min(len(expected_items), len(actual_items))
    for i in range(paired):
        out.extend(_score_one_item(expected_items[i], actual_items[i], i))

    # 3) Penalize extra/missing items as strict zeros on a single virtual field
    # so accuracy is honest. (We could expand to per-extra-item zeros but that
    # would dominate scoring on a single bad doc; one combined penalty is fine.)
    delta = abs(len(expected_items) - len(actual_items))
    if delta > 0:
        out.append(_fail(
            "items.coverage", "strict",
            f"{len(expected_items)} expected",
            f"{len(actual_items)} actual",
            f"{delta} unmatched item(s)",
        ))

    return out


def _score_one_item(e: LineItem, a: LineItem, idx: int) -> list[FieldResult]:
    base = f"items[{idx}]"
    out: list[FieldResult] = [
        # Description: semantic with Jaccard >= 0.85
        _semantic_text(
            f"{base}.description", e.description, a.description, NAME_DESC_JACCARD_THRESHOLD
        ),
        # Quantity: strict (Decimal compare)
        _decimal_equal(f"{base}.quantity", e.quantity, a.quantity),
        # Unit: strict equal (string or None)
        _strict_equal(
            f"{base}.unit", _strip_or_none(e.unit), _strip_or_none(a.unit)
        ),
        # VAT treatment: strict
        _strict_equal(f"{base}.vat_treatment", e.vat_treatment, a.vat_treatment),
        # Identifiers: strict equal
        _strict_equal(
            f"{base}.sku", _strip_or_none(e.sku), _strip_or_none(a.sku)
        ),
        _strict_equal(
            f"{base}.barcode", _strip_or_none(e.barcode), _strip_or_none(a.barcode)
        ),
        _strict_equal(
            f"{base}.item_code",
            _strip_or_none(e.item_code),
            _strip_or_none(a.item_code),
        ),
    ]
    # Money fields (strict)
    out.extend(_money_field(f"{base}.unit_price", e.unit_price, a.unit_price))
    out.extend(_money_field(f"{base}.subtotal", e.subtotal, a.subtotal))
    out.extend(_money_field(f"{base}.vat_amount", e.vat_amount, a.vat_amount))
    out.extend(_money_field(f"{base}.total", e.total, a.total))
    out.extend(_money_field(f"{base}.excise_amount", e.excise_amount, a.excise_amount))
    # sub_charges: order-independent set of Money
    out.append(_sub_charges_field(f"{base}.sub_charges", e.sub_charges, a.sub_charges))
    return out


# ---------------------------------------------------------------------------
# Transport block
# ---------------------------------------------------------------------------

def _score_transport(
    e: TransportInfo | None, a: TransportInfo | None
) -> list[FieldResult]:
    out: list[FieldResult] = []
    if e is None and a is None:
        out.append(_pass("transport", "strict", None, None, "both None"))
        return out
    if e is None or a is None:
        out.append(_fail("transport", "strict", e, a, "presence mismatch"))
        return out

    out.append(_strict_equal(
        "transport.start_address",
        _strip_or_none(e.start_address),
        _strip_or_none(a.start_address),
    ))
    out.append(_strict_equal(
        "transport.end_address",
        _strip_or_none(e.end_address),
        _strip_or_none(a.end_address),
    ))
    out.append(_strict_equal(
        "transport.vehicle_plate",
        _strip_or_none(e.vehicle_plate),
        _strip_or_none(a.vehicle_plate),
    ))
    out.append(_strict_equal("transport.has_trailer", e.has_trailer, a.has_trailer))
    out.append(_strict_equal(
        "transport.transport_cost_payer",
        e.transport_cost_payer,
        a.transport_cost_payer,
    ))
    out.append(_strict_equal("transport.begin_date", e.begin_date, a.begin_date))
    out.append(_strict_equal(
        "transport.delivery_date", e.delivery_date, a.delivery_date
    ))
    out.extend(_money_field(
        "transport.transport_cost", e.transport_cost, a.transport_cost
    ))
    # Driver is a Party — reuse party scoring.
    out.extend(_score_party(e.driver, a.driver, "transport.driver"))
    return out


# ---------------------------------------------------------------------------
# Free-text fields (topic coverage)
# ---------------------------------------------------------------------------

def _score_free_text(e: CanonicalInvoice, a: CanonicalInvoice) -> list[FieldResult]:
    out: list[FieldResult] = []
    out.extend(_score_free_text_field(
        "vat_treatment_reason", e.vat_treatment_reason, a.vat_treatment_reason
    ))
    out.extend(_score_extraction_notes(e.extraction_notes, a.extraction_notes))
    return out


def _score_free_text_field(
    path: str, expected: str | None, actual: str | None
) -> list[FieldResult]:
    # Both None = pass (no expected content, no content surfaced)
    if expected is None and actual is None:
        return [_pass(path, "free_text", None, None, "both None")]
    if expected is None and actual is not None:
        # Actual added content the label didn't expect. Don't penalize — this
        # is the "extra notes" case; honest-nulls is the prompt's contract.
        return [_pass(path, "free_text", None, actual, "expected None; actual added content (not penalized)")]
    if expected is not None and actual is None:
        return [_fail(path, "free_text", expected, None, "missing content")]

    score = _topic_coverage(expected, [actual])  # type: ignore[arg-type,list-item]
    return [
        FieldResult(
            path=path,
            tier="free_text",
            expected=expected,
            actual=actual,
            correct=score >= 1.0,
            score=score,
            note=f"topic coverage {score:.2f}",
        )
    ]


def _score_extraction_notes(
    expected: list[str], actual: list[str]
) -> list[FieldResult]:
    # extraction_notes is scored as: for each expected note, what fraction
    # of its key tokens appear anywhere in the union of actual notes?
    # Final score = mean across expected notes.
    if not expected:
        return [_pass(
            "extraction_notes", "free_text", [], actual, "no expected notes"
        )]
    per_note_scores = [_topic_coverage(note, actual) for note in expected]
    mean_score = sum(per_note_scores) / len(per_note_scores)
    return [
        FieldResult(
            path="extraction_notes",
            tier="free_text",
            expected=expected,
            actual=actual,
            correct=mean_score >= 1.0,
            score=mean_score,
            note=f"mean topic coverage {mean_score:.2f} across {len(expected)} expected note(s)",
        )
    ]


def _topic_coverage(expected_text: str, actual_texts: list[str]) -> float:
    expected_tokens = {
        t for t in _tokenize(expected_text) if t not in _STOPWORDS
    }
    if not expected_tokens:
        return 1.0
    actual_pool: set[str] = set()
    for t in actual_texts:
        actual_pool.update(_tokenize(t))
    covered = expected_tokens & actual_pool
    return len(covered) / len(expected_tokens)


# ---------------------------------------------------------------------------
# Field-level primitives
# ---------------------------------------------------------------------------

def _strict_equal(
    path: str, expected: Any, actual: Any, note: str | None = None
) -> FieldResult:
    correct = expected == actual
    return FieldResult(
        path=path,
        tier="strict",
        expected=_jsonable(expected),
        actual=_jsonable(actual),
        correct=correct,
        score=1.0 if correct else 0.0,
        note=note,
    )


def _doc_number(path: str, e: str | None, a: str | None) -> FieldResult:
    # Per the plan, whitespace-strip + case-fold only. Do NOT re-implement
    # family-specific rules (DRESSUP strips '#', etc.) — that's the prompt's
    # job. The strict match catches misalignment between prompt and labels.
    en = _norm_doc_num(e)
    an = _norm_doc_num(a)
    correct = en == an
    return FieldResult(
        path=path,
        tier="strict",
        expected=e,
        actual=a,
        correct=correct,
        score=1.0 if correct else 0.0,
        note="whitespace-stripped + case-folded compare" if not correct else None,
    )


def _norm_doc_num(s: str | None) -> str | None:
    if s is None:
        return None
    return s.strip().casefold()


def _tin_field(path: str, e: str | None, a: str | None) -> FieldResult:
    # TINs: strip ALL whitespace, internal too. The schema docstring is
    # explicit: '205 025 676' should normalize to '205025676'. We mirror
    # that on comparison so trivial formatting from the model isn't
    # penalized as a wrong TIN.
    en = _strip_all_whitespace(e)
    an = _strip_all_whitespace(a)
    correct = en == an
    return FieldResult(
        path=path,
        tier="strict",
        expected=e,
        actual=a,
        correct=correct,
        score=1.0 if correct else 0.0,
    )


def _decimal_equal(path: str, e: Decimal, a: Decimal) -> FieldResult:
    # Decimal __eq__ compares numerically, so Decimal('1.0') == Decimal('1.00')
    # We preserve original precision in the FieldResult for debugging.
    correct = e == a
    return FieldResult(
        path=path,
        tier="strict",
        expected=str(e),
        actual=str(a),
        correct=correct,
        score=1.0 if correct else 0.0,
    )


def _money_field(
    path: str, e: Money | None, a: Money | None
) -> list[FieldResult]:
    # Presence first, then amount + currency.
    if e is None and a is None:
        return [_pass(path, "strict", None, None, "both None")]
    if e is None or a is None:
        return [_fail(path, "strict", _jsonable(e), _jsonable(a), "presence mismatch")]

    amount_correct = e.amount == a.amount
    currency_correct = e.currency == a.currency
    correct = amount_correct and currency_correct
    note: str | None = None
    if not correct:
        parts = []
        if not amount_correct:
            parts.append(f"amount {e.amount} vs {a.amount}")
        if not currency_correct:
            parts.append(f"currency {e.currency.value} vs {a.currency.value}")
        note = "; ".join(parts)
    return [
        FieldResult(
            path=path,
            tier="strict",
            expected={"amount": str(e.amount), "currency": e.currency.value},
            actual={"amount": str(a.amount), "currency": a.currency.value},
            correct=correct,
            score=1.0 if correct else 0.0,
            note=note,
        )
    ]


def _sub_charges_field(
    path: str, e: list[Money], a: list[Money]
) -> FieldResult:
    # Order-independent set compare. Money is hashable (frozen dataclass) so
    # set semantics work, but Pydantic v2 frozen=True isn't true hashing —
    # we tuple-ize amount+currency.
    es = {(m.amount, m.currency) for m in e}
    as_ = {(m.amount, m.currency) for m in a}
    correct = es == as_
    return FieldResult(
        path=path,
        tier="strict",
        expected=[{"amount": str(m.amount), "currency": m.currency.value} for m in e],
        actual=[{"amount": str(m.amount), "currency": m.currency.value} for m in a],
        correct=correct,
        score=1.0 if correct else 0.0,
        note=(
            None if correct
            else f"sub_charges set mismatch (expected {len(es)}, actual {len(as_)})"
        ),
    )


def _semantic_text(
    path: str, e: str | None, a: str | None, threshold: float
) -> FieldResult:
    # Presence-aware semantic compare.
    if e is None and a is None:
        return _pass(path, "semantic", None, None, "both None")
    if e is None or a is None:
        return _fail(path, "semantic", e, a, "presence mismatch")

    en = e.strip()
    an = a.strip()
    if en.casefold() == an.casefold():
        return _pass(path, "semantic", e, a, "exact match (case-insensitive)")

    score = _jaccard_tokens(en, an)
    correct = score >= threshold
    return FieldResult(
        path=path,
        tier="semantic",
        expected=e,
        actual=a,
        correct=correct,
        score=1.0 if correct else score,
        note=f"Jaccard {score:.2f} vs threshold {threshold:.2f}",
    )


def _pass(
    path: str, tier: Tier, expected: Any, actual: Any, note: str | None = None
) -> FieldResult:
    return FieldResult(
        path=path,
        tier=tier,
        expected=_jsonable(expected),
        actual=_jsonable(actual),
        correct=True,
        score=1.0,
        note=note,
    )


def _fail(
    path: str, tier: Tier, expected: Any, actual: Any, note: str | None = None
) -> FieldResult:
    return FieldResult(
        path=path,
        tier=tier,
        expected=_jsonable(expected),
        actual=_jsonable(actual),
        correct=False,
        score=0.0,
        note=note,
    )


# ---------------------------------------------------------------------------
# Fallback: actual is None (parse failure). Score every conceivable field 0.
# ---------------------------------------------------------------------------

def _all_zero_fields(e: CanonicalInvoice, reason: str) -> list[FieldResult]:
    """When the model didn't produce valid CanonicalInvoice JSON, treat every
    field as wrong. We synthesize the field paths from the expected document
    so accuracy is comparable to non-parse-failure runs."""
    out: list[FieldResult] = []

    def fail(path: str, tier: Tier, expected: Any) -> None:
        out.append(FieldResult(
            path=path, tier=tier, expected=_jsonable(expected), actual=None,
            correct=False, score=0.0, note=f"parse failure: {reason}",
        ))

    fail("accepted", "strict", e.accepted)
    fail("document_type", "strict", e.document_type)
    fail("document_number", "strict", e.document_number)
    fail("document_date", "strict", e.document_date)
    fail("document_currency", "strict", e.document_currency)
    fail("grand_total", "strict", _jsonable(e.grand_total))
    if e.seller:
        fail("seller.tin", "strict", e.seller.tin)
        fail("seller.name", "semantic", e.seller.name)
    if e.buyer:
        fail("buyer.tin", "strict", e.buyer.tin)
        fail("buyer.name", "semantic", e.buyer.name)
    for i, item in enumerate(e.items):
        fail(f"items[{i}].description", "semantic", item.description)
        fail(f"items[{i}].total", "strict", _jsonable(item.total))
    return out


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TOKEN_RE = re.compile(r"[^\W_]+", flags=re.UNICODE)


def _tokenize(text: str) -> set[str]:
    """Casefold and split on non-letter/digit boundaries. Unicode-aware."""
    return {m.group(0).casefold() for m in _TOKEN_RE.finditer(text or "")}


def _jaccard_tokens(a: str, b: str) -> float:
    ta = _tokenize(a)
    tb = _tokenize(b)
    if not ta and not tb:
        return 1.0
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def _strip_or_none(s: str | None) -> str | None:
    if s is None:
        return None
    stripped = s.strip()
    return stripped if stripped else None


def _strip_all_whitespace(s: str | None) -> str | None:
    if s is None:
        return None
    return "".join(s.split()) or None


def _jsonable(v: Any) -> Any:
    """Convert Pydantic / Decimal / date / enum to JSON-serializable primitives.

    Used so FieldResult.expected/actual round-trip through json.dump() cleanly.
    Falls back to repr() for anything obscure (the field result is for human
    debugging, not for re-deserialization).
    """
    if v is None:
        return None
    if isinstance(v, (bool, int, float, str)):
        # Reject NaN floats — they break JSON
        if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            return repr(v)
        return v
    if isinstance(v, Decimal):
        return str(v)
    if hasattr(v, "value") and hasattr(v, "name"):  # Enum
        return v.value
    if hasattr(v, "isoformat"):  # date / datetime
        return v.isoformat()
    if isinstance(v, dict):
        return {k: _jsonable(x) for k, x in v.items()}
    if isinstance(v, (list, tuple, set, frozenset)):
        return [_jsonable(x) for x in v]
    # Pydantic model
    if hasattr(v, "model_dump"):
        return v.model_dump(mode="json")
    return repr(v)

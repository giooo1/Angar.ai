"""Unit tests for eval.comparator.

Hand-built CanonicalInvoice pairs covering each scoring tier, the tricky
Decimal/Money handling, sub_charges set semantics, transport descent,
payment-order rejection scoring, and parse-failure fallback.

No Anthropic API calls — these are pure comparator tests.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

import pytest

from eval import canonical_path  # noqa: F401
from canonical import (  # noqa: E402
    CanonicalInvoice,
    Currency,
    DocumentType,
    ExtractionMetadata,
    LineItem,
    Money,
    Party,
    PartyType,
    Script,
    TransportInfo,
    VATTreatment,
)
from eval.comparator import (  # noqa: E402
    TIER_WEIGHT,
    DocResult,
    FieldResult,
    _jaccard_tokens,
    _topic_coverage,
    compare,
)


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------

def _meta() -> ExtractionMetadata:
    return ExtractionMetadata(
        source_filename="test.pdf",
        source_pdf_sha256="abc",
        extracted_at=datetime(2026, 1, 1),
        model_version="test",
        prompt_version="test",
    )


def _invoice(**overrides) -> CanonicalInvoice:
    """Minimal accepted=True invoice. Override any field via kwargs."""
    defaults = dict(
        accepted=True,
        document_type=DocumentType.REGULAR_INVOICE,
        document_number="INV-1",
        document_date=date(2026, 1, 1),
        document_currency=Currency.GEL,
        seller=Party(name="Acme LLC", tin="123456789", tin_label_present=True,
                     party_type=PartyType.LEGAL_ENTITY, script=Script.LATIN),
        buyer=Party(name="Buyer LLC", tin="987654321", tin_label_present=True,
                    party_type=PartyType.LEGAL_ENTITY, script=Script.LATIN),
        items=[
            LineItem(
                description="Widget",
                quantity=Decimal("2"),
                unit_price=Money(amount=Decimal("10.00"), currency=Currency.GEL),
                total=Money(amount=Decimal("20.00"), currency=Currency.GEL),
            )
        ],
        grand_total=Money(amount=Decimal("20.00"), currency=Currency.GEL),
        extraction=_meta(),
    )
    defaults.update(overrides)
    return CanonicalInvoice(**defaults)


def _field(result: DocResult, path: str) -> FieldResult:
    """Find one field by path in a result; helpful for assertions."""
    for f in result.fields:
        if f.path == path:
            return f
    raise AssertionError(f"No field {path!r} in result. Available: "
                         f"{[f.path for f in result.fields]}")


# ---------------------------------------------------------------------------
# Tier weights and the spec
# ---------------------------------------------------------------------------

def test_tier_weights_match_phase3_spec() -> None:
    """Phase 3 §5.2 commits to these exact weights."""
    assert TIER_WEIGHT["strict"] == 0.90
    assert TIER_WEIGHT["semantic"] == 0.60
    assert TIER_WEIGHT["free_text"] == 0.30


# ---------------------------------------------------------------------------
# Strict-tier scoring
# ---------------------------------------------------------------------------

class TestStrictTier:
    def test_identical_invoices_score_perfect(self) -> None:
        inv = _invoice()
        result = compare(inv, inv)
        assert result.weighted_accuracy == 1.0
        assert all(f.correct for f in result.fields)

    def test_document_number_whitespace_and_case_normalized(self) -> None:
        e = _invoice(document_number="INV-1")
        a = _invoice(document_number="  inv-1  ")
        result = compare(e, a)
        assert _field(result, "document_number").correct

    def test_document_number_different_fails(self) -> None:
        e = _invoice(document_number="INV-1")
        a = _invoice(document_number="INV-2")
        result = compare(e, a)
        assert not _field(result, "document_number").correct

    def test_tin_whitespace_stripped(self) -> None:
        e = _invoice(seller=Party(
            name="x", tin="123456789", tin_label_present=True,
            party_type=PartyType.LEGAL_ENTITY, script=Script.LATIN,
        ))
        a = _invoice(seller=Party(
            name="x", tin="  123 456 789  ", tin_label_present=True,
            party_type=PartyType.LEGAL_ENTITY, script=Script.LATIN,
        ))
        # Spaces in TIN should still pass strict (the schema docstring says
        # the TIN field should be whitespace-stripped on extraction; we mirror
        # that on comparison to avoid false negatives from minor formatting).
        result = compare(e, a)
        # Note: this also exercises the seller.name "exact match (case-insensitive)" path.
        assert _field(result, "seller.tin").correct

    def test_decimal_precision_does_not_matter(self) -> None:
        """Decimal('20.00') == Decimal('20.0') == Decimal('20') numerically."""
        e = _invoice(grand_total=Money(amount=Decimal("20.00"), currency=Currency.GEL))
        a = _invoice(grand_total=Money(amount=Decimal("20.0"), currency=Currency.GEL))
        result = compare(e, a)
        assert _field(result, "grand_total").correct

    def test_money_none_vs_zero_is_mismatch(self) -> None:
        """Honest nulls: None != Money(0, GEL). Phase 3 spec is explicit on this."""
        e = _invoice(vat_total=None)
        a = _invoice(vat_total=Money(amount=Decimal("0"), currency=Currency.GEL))
        result = compare(e, a)
        f = _field(result, "vat_total")
        assert not f.correct
        assert "presence mismatch" in (f.note or "")

    def test_money_amount_mismatch_records_both(self) -> None:
        e = _invoice(grand_total=Money(amount=Decimal("20.00"), currency=Currency.GEL))
        a = _invoice(grand_total=Money(amount=Decimal("21.00"), currency=Currency.GEL))
        result = compare(e, a)
        f = _field(result, "grand_total")
        assert not f.correct
        assert "amount 20.00 vs 21.00" in (f.note or "")

    def test_money_currency_mismatch_recorded(self) -> None:
        e = _invoice(grand_total=Money(amount=Decimal("20.00"), currency=Currency.GEL))
        a = _invoice(grand_total=Money(amount=Decimal("20.00"), currency=Currency.USD))
        result = compare(e, a)
        f = _field(result, "grand_total")
        assert not f.correct
        assert "currency GEL vs USD" in (f.note or "")


# ---------------------------------------------------------------------------
# Sub_charges set semantics
# ---------------------------------------------------------------------------

class TestSubCharges:
    def test_order_independent_match(self) -> None:
        a_money = Money(amount=Decimal("455.00"), currency=Currency.GEL)
        b_money = Money(amount=Decimal("200.00"), currency=Currency.GEL)
        e = _invoice(items=[LineItem(
            description="x", quantity=Decimal("1"),
            unit_price=Money(amount=Decimal("1"), currency=Currency.GEL),
            total=Money(amount=Decimal("1"), currency=Currency.GEL),
            sub_charges=[a_money, b_money],
        )])
        a = _invoice(items=[LineItem(
            description="x", quantity=Decimal("1"),
            unit_price=Money(amount=Decimal("1"), currency=Currency.GEL),
            total=Money(amount=Decimal("1"), currency=Currency.GEL),
            sub_charges=[b_money, a_money],  # reordered
        )])
        result = compare(e, a)
        assert _field(result, "items[0].sub_charges").correct

    def test_both_empty_passes(self) -> None:
        e = _invoice()  # default item has sub_charges=[]
        a = _invoice()
        result = compare(e, a)
        assert _field(result, "items[0].sub_charges").correct

    def test_mismatch_in_set_fails(self) -> None:
        e = _invoice(items=[LineItem(
            description="x", quantity=Decimal("1"),
            unit_price=Money(amount=Decimal("1"), currency=Currency.GEL),
            total=Money(amount=Decimal("1"), currency=Currency.GEL),
            sub_charges=[Money(amount=Decimal("100"), currency=Currency.GEL)],
        )])
        a = _invoice(items=[LineItem(
            description="x", quantity=Decimal("1"),
            unit_price=Money(amount=Decimal("1"), currency=Currency.GEL),
            total=Money(amount=Decimal("1"), currency=Currency.GEL),
            sub_charges=[Money(amount=Decimal("200"), currency=Currency.GEL)],
        )])
        result = compare(e, a)
        assert not _field(result, "items[0].sub_charges").correct


# ---------------------------------------------------------------------------
# Semantic tier
# ---------------------------------------------------------------------------

class TestSemanticTier:
    def test_exact_case_insensitive_passes(self) -> None:
        e = _invoice(seller=Party(
            name="ACME LLC", tin="1", tin_label_present=True,
            party_type=PartyType.LEGAL_ENTITY, script=Script.LATIN,
        ))
        a = _invoice(seller=Party(
            name="acme llc", tin="1", tin_label_present=True,
            party_type=PartyType.LEGAL_ENTITY, script=Script.LATIN,
        ))
        result = compare(e, a)
        f = _field(result, "seller.name")
        assert f.correct and f.score == 1.0

    def test_high_jaccard_passes(self) -> None:
        """Jaccard 4/5 = 0.8 — below 0.85 threshold so should NOT pass."""
        e = _invoice(seller=Party(
            name="Acme LLC software services group",
            tin="1", tin_label_present=True,
            party_type=PartyType.LEGAL_ENTITY, script=Script.LATIN,
        ))
        a = _invoice(seller=Party(
            name="Acme LLC software services",
            tin="1", tin_label_present=True,
            party_type=PartyType.LEGAL_ENTITY, script=Script.LATIN,
        ))
        result = compare(e, a)
        f = _field(result, "seller.name")
        # 4 common tokens / 5 total unique = 0.8 < 0.85 threshold
        assert not f.correct
        assert 0.79 < f.score < 0.81

    def test_low_jaccard_fails_with_partial_score(self) -> None:
        e = _invoice(seller=Party(
            name="Acme LLC", tin="1", tin_label_present=True,
            party_type=PartyType.LEGAL_ENTITY, script=Script.LATIN,
        ))
        a = _invoice(seller=Party(
            name="Different Company Name Entirely", tin="1", tin_label_present=True,
            party_type=PartyType.LEGAL_ENTITY, script=Script.LATIN,
        ))
        result = compare(e, a)
        f = _field(result, "seller.name")
        assert not f.correct
        assert 0.0 <= f.score < 0.5

    def test_address_uses_lower_threshold(self) -> None:
        """Addresses use 0.70 threshold per Phase 3 spec (vs 0.85 for names)."""
        # ~0.75 Jaccard — passes for address, fails for name
        e = _invoice(seller=Party(
            name="x", tin="1", tin_label_present=True,
            party_type=PartyType.LEGAL_ENTITY, script=Script.LATIN,
            address="123 Main Street Tbilisi Georgia",
        ))
        a = _invoice(seller=Party(
            name="x", tin="1", tin_label_present=True,
            party_type=PartyType.LEGAL_ENTITY, script=Script.LATIN,
            address="123 Main Street Tbilisi",  # 4 of 5 = 0.8 Jaccard
        ))
        result = compare(e, a)
        assert _field(result, "seller.address").correct


# ---------------------------------------------------------------------------
# Free-text tier
# ---------------------------------------------------------------------------

class TestFreeTextTier:
    def test_topic_coverage_perfect(self) -> None:
        score = _topic_coverage(
            "discount applied at document level not per line",
            ["The discount applied at document level not per line"],
        )
        assert score == 1.0

    def test_topic_coverage_partial(self) -> None:
        score = _topic_coverage(
            "phone number 557115503 under buyer is not a TIN",
            ["the number 557115503 is a phone"],  # missing 'buyer', 'tin', 'under'
        )
        assert 0.0 < score < 1.0

    def test_topic_coverage_excludes_stopwords(self) -> None:
        score = _topic_coverage(
            "the discount is at the document level",
            ["discount document level"],  # captures all non-stopword tokens
        )
        assert score == 1.0

    def test_topic_coverage_empty_expected_is_pass(self) -> None:
        # Edge case: no expected content means nothing to cover, so 1.0.
        assert _topic_coverage("", ["whatever"]) == 1.0

    def test_extraction_notes_mean_score(self) -> None:
        e = _invoice(extraction_notes=[
            "discount applied at document level",
            "regular price column is RRP not charged",
        ])
        a = _invoice(extraction_notes=[
            "the discount applied at document level",
            "we used the regular price column, RRP",  # missing 'not', 'charged'
        ])
        result = compare(e, a)
        f = _field(result, "extraction_notes")
        # First note fully covered (1.0); second partial. Mean should be < 1.0.
        assert 0.5 < f.score <= 1.0

    def test_actual_adds_extra_content_not_penalized(self) -> None:
        e = _invoice(vat_treatment_reason=None)
        a = _invoice(vat_treatment_reason="some extra context")
        result = compare(e, a)
        assert _field(result, "vat_treatment_reason").correct

    def test_missing_actual_content_fails(self) -> None:
        e = _invoice(vat_treatment_reason="B2C consumer sale")
        a = _invoice(vat_treatment_reason=None)
        result = compare(e, a)
        assert not _field(result, "vat_treatment_reason").correct


# ---------------------------------------------------------------------------
# Item count + per-item scoring
# ---------------------------------------------------------------------------

class TestItems:
    def test_count_mismatch_records_two_failures(self) -> None:
        item = LineItem(
            description="x", quantity=Decimal("1"),
            unit_price=Money(amount=Decimal("1"), currency=Currency.GEL),
            total=Money(amount=Decimal("1"), currency=Currency.GEL),
        )
        e = _invoice(items=[item, item, item])  # 3 items
        a = _invoice(items=[item])  # 1 item
        result = compare(e, a)
        assert not _field(result, "items.count").correct
        assert not _field(result, "items.coverage").correct

    def test_count_match_no_coverage_field(self) -> None:
        e = _invoice()
        a = _invoice()
        result = compare(e, a)
        assert _field(result, "items.count").correct
        # When counts match, items.coverage isn't added.
        assert "items.coverage" not in [f.path for f in result.fields]


# ---------------------------------------------------------------------------
# Transport descent
# ---------------------------------------------------------------------------

class TestTransport:
    def test_both_none_passes(self) -> None:
        result = compare(_invoice(transport=None), _invoice(transport=None))
        assert _field(result, "transport").correct

    def test_presence_mismatch_fails(self) -> None:
        e = _invoice(transport=None)
        a = _invoice(transport=TransportInfo(start_address="x"))
        result = compare(e, a)
        assert not _field(result, "transport").correct

    def test_descends_into_subfields(self) -> None:
        t = TransportInfo(
            start_address="origin",
            end_address="destination",
            vehicle_plate="AA001AA",
            has_trailer=False,
        )
        result = compare(_invoice(transport=t), _invoice(transport=t))
        assert _field(result, "transport.vehicle_plate").correct
        assert _field(result, "transport.has_trailer").correct


# ---------------------------------------------------------------------------
# Rejection (accepted=False) special-case scoring
# ---------------------------------------------------------------------------

class TestRejection:
    def test_only_rejection_relevant_fields_scored(self) -> None:
        rejected = CanonicalInvoice(
            accepted=False,
            rejection_reason="bank payment order, not an invoice",
            document_type=DocumentType.PAYMENT_ORDER,
            document_number="6509299",
            document_currency=Currency.GEL,
            grand_total=Money(amount=Decimal("200.00"), currency=Currency.GEL),
            references_other_document=None,
            extraction=_meta(),
        )
        result = compare(rejected, rejected)
        paths = {f.path for f in result.fields}
        # These should be present
        assert "accepted" in paths
        assert "document_type" in paths
        assert "rejection_reason" in paths
        assert "grand_total" in paths
        # These should NOT be scored on rejected docs
        assert "items.count" not in paths
        assert "seller.name" not in paths
        assert "buyer.tin" not in paths

    def test_rejection_with_matching_fields_is_perfect(self) -> None:
        rejected = CanonicalInvoice(
            accepted=False,
            rejection_reason="payment order",
            document_type=DocumentType.PAYMENT_ORDER,
            document_number="6509299",
            document_currency=Currency.GEL,
            grand_total=Money(amount=Decimal("200.00"), currency=Currency.GEL),
            extraction=_meta(),
        )
        result = compare(rejected, rejected)
        assert result.weighted_accuracy == 1.0


# ---------------------------------------------------------------------------
# Parse-failure fallback
# ---------------------------------------------------------------------------

class TestParseFailure:
    def test_actual_none_scores_zero(self) -> None:
        result = compare(_invoice(), None, fixture_name="test", parse_error="json decode failed")
        assert result.weighted_accuracy == 0.0
        assert result.parse_error == "json decode failed"
        # All synthesized fields should be failures
        assert all(not f.correct for f in result.fields)

    def test_parse_error_propagated_to_field_notes(self) -> None:
        result = compare(_invoice(), None, parse_error="boom")
        assert all("boom" in (f.note or "") for f in result.fields)


# ---------------------------------------------------------------------------
# Weighted accuracy math
# ---------------------------------------------------------------------------

class TestWeightedAccuracy:
    def test_all_strict_correct_is_one(self) -> None:
        # Identical invoices — every field 1.0, weighted average is 1.0.
        result = compare(_invoice(), _invoice())
        assert result.weighted_accuracy == 1.0

    def test_weighting_favors_strict(self) -> None:
        """A failure on one strict field should hurt more than one semantic miss.

        We build two scenarios: (1) one strict field wrong; (2) one semantic
        field wrong. Both invoices have the same set of fields. The strict
        miss should produce a lower weighted_accuracy than the semantic miss.
        """
        # Scenario 1: strict miss on document_number
        e1 = _invoice(document_number="A")
        a1 = _invoice(document_number="B")
        # Scenario 2: semantic miss on seller.name
        e2 = _invoice(seller=Party(
            name="Alpha", tin="1", tin_label_present=True,
            party_type=PartyType.LEGAL_ENTITY, script=Script.LATIN,
        ))
        a2 = _invoice(seller=Party(
            name="Completely Different Name Here", tin="1", tin_label_present=True,
            party_type=PartyType.LEGAL_ENTITY, script=Script.LATIN,
        ))
        assert compare(e1, a1).weighted_accuracy < compare(e2, a2).weighted_accuracy


# ---------------------------------------------------------------------------
# Token helpers
# ---------------------------------------------------------------------------

class TestTokenHelpers:
    def test_jaccard_identical_strings(self) -> None:
        assert _jaccard_tokens("hello world", "hello world") == 1.0

    def test_jaccard_disjoint(self) -> None:
        assert _jaccard_tokens("a b", "c d") == 0.0

    def test_jaccard_partial(self) -> None:
        # {a,b} ∩ {a,c} = {a} → 1 shared; {a,b} ∪ {a,c} = {a,b,c} → 3 union; J = 1/3
        assert abs(_jaccard_tokens("a b", "a c") - 1/3) < 1e-9

    def test_jaccard_unicode_tokens(self) -> None:
        # Georgian text should tokenize correctly under unicode-aware regex.
        assert _jaccard_tokens("საქართველო თბილისი", "საქართველო თბილისი") == 1.0

    def test_jaccard_case_insensitive(self) -> None:
        assert _jaccard_tokens("Hello World", "hello world") == 1.0

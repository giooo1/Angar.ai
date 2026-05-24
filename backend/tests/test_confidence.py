"""Tests for compute_field_confidence (WS2)."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from angar_schema.canonical import (
    CanonicalInvoice,
    Currency,
    DocumentType,
    ExtractionMetadata,
    LineItem,
    Money,
    Party,
    PartyType,
    Script,
    VATTreatment,
)
from backend.confidence import (
    CROSS_CHECK_FAIL,
    FORMAT_OFF,
    MISSING,
    PERFECT,
    SUSPICIOUS,
    compute_field_confidence,
)


def _meta() -> ExtractionMetadata:
    return ExtractionMetadata(
        source_filename="x.pdf",
        source_pdf_sha256="abc",
        extracted_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        model_version="claude-sonnet-4-6",
        prompt_version="v3",
    )


def _money(amount: str, ccy: Currency = Currency.GEL) -> Money:
    return Money(amount=Decimal(amount), currency=ccy)


def _line(total: str = "100.00") -> LineItem:
    return LineItem(
        description="x",
        quantity=Decimal("1"),
        unit_price=_money(total),
        total=_money(total),
        vat_treatment=VATTreatment.STANDARD,
    )


def _full_invoice(**overrides) -> CanonicalInvoice:
    """Clean, totals-reconciling invoice with both parties populated."""
    base = dict(
        accepted=True,
        document_type=DocumentType.REGULAR_INVOICE,
        document_number="INV-1",
        document_date="2026-05-12",
        document_currency=Currency.GEL,
        seller=Party(
            name="Vertex Logistics",
            tin="GE405998721",
            tin_label_present=True,
            party_type=PartyType.LEGAL_ENTITY,
            address="Tbilisi, Rustaveli 24",
            script=Script.LATIN,
        ),
        buyer=Party(
            name="Mtkvari & Co",
            tin="GE402998117",
            tin_label_present=True,
            party_type=PartyType.LEGAL_ENTITY,
            address="Tbilisi",
            script=Script.MIXED,
        ),
        items=[_line("2450.00")],
        subtotal_total=_money("2450.00"),
        vat_total=_money("441.00"),
        grand_total=_money("2891.00"),
        extraction=_meta(),
    )
    base.update(overrides)
    return CanonicalInvoice(**base)


class TestPerfectInvoice:
    def test_everything_high(self):
        c = _full_invoice()
        s = compute_field_confidence(c)
        # All ~15 expected keys present.
        expected = {
            "seller.name", "seller.tin", "seller.party_type", "seller.address",
            "buyer.name", "buyer.tin", "buyer.party_type", "buyer.address",
            "document_number", "document_date", "document_currency",
            "subtotal_total.amount", "vat_total.amount", "grand_total.amount",
            "items",
        }
        assert set(s.keys()) == expected
        for k, v in s.items():
            assert v >= 0.85, f"{k} should be high but is {v}"


class TestMissingFields:
    def test_null_tin_scores_missing(self):
        c = _full_invoice(
            seller=Party(name="X", tin=None, party_type=PartyType.LEGAL_ENTITY, script=Script.LATIN),
        )
        assert compute_field_confidence(c)["seller.tin"] == MISSING

    def test_null_buyer_scores_all_buyer_fields_missing(self):
        c = _full_invoice(buyer=None)
        s = compute_field_confidence(c)
        for k in ("buyer.name", "buyer.tin", "buyer.party_type", "buyer.address"):
            assert s[k] == MISSING

    def test_empty_items_list_scores_missing(self):
        c = _full_invoice(items=[])
        assert compute_field_confidence(c)["items"] == MISSING


class TestFormatChecks:
    def test_malformed_tin_lowers_to_format_off(self):
        c = _full_invoice(
            seller=Party(
                name="X",
                tin="12345",  # too short, no GE prefix
                party_type=PartyType.LEGAL_ENTITY,
                script=Script.LATIN,
            ),
        )
        assert compute_field_confidence(c)["seller.tin"] == FORMAT_OFF

    def test_well_formed_tin_with_or_without_ge_prefix_is_perfect(self):
        for tin in ("GE405998721", "405998721", "GE 405 998 721", "405 998 721"):
            c = _full_invoice(
                seller=Party(
                    name="X", tin=tin, party_type=PartyType.LEGAL_ENTITY, script=Script.LATIN,
                ),
            )
            assert compute_field_confidence(c)["seller.tin"] == PERFECT, tin

    def test_missing_date_scores_missing(self):
        c = _full_invoice(document_date=None)
        assert compute_field_confidence(c)["document_date"] == MISSING


class TestSuspiciousValues:
    def test_na_address_scores_suspicious(self):
        c = _full_invoice(
            seller=Party(
                name="X", tin="GE111111111", party_type=PartyType.LEGAL_ENTITY,
                address="N/A", script=Script.LATIN,
            ),
        )
        assert compute_field_confidence(c)["seller.address"] == SUSPICIOUS

    def test_unknown_party_type_scores_suspicious(self):
        c = _full_invoice(
            seller=Party(
                name="X", tin="GE111111111", party_type=PartyType.UNKNOWN,
                script=Script.LATIN,
            ),
        )
        assert compute_field_confidence(c)["seller.party_type"] == SUSPICIOUS


class TestTotalsCrossCheck:
    def test_mismatch_drops_grand_total_to_cross_check_fail(self):
        # Subtotal 100 + VAT 18 should equal 118; we set grand_total to 200.
        c = _full_invoice(
            items=[_line("100.00")],
            subtotal_total=_money("100.00"),
            vat_total=_money("18.00"),
            grand_total=_money("200.00"),
        )
        s = compute_field_confidence(c)
        assert s["grand_total.amount"] == CROSS_CHECK_FAIL
        # Subtotal + VAT are still present; they get penalized too because
        # the cross-check is whole-totals-block scoped.
        assert s["subtotal_total.amount"] == CROSS_CHECK_FAIL
        assert s["vat_total.amount"] == CROSS_CHECK_FAIL

    def test_reconciling_totals_are_perfect(self):
        c = _full_invoice(
            items=[_line("100.00")],
            subtotal_total=_money("100.00"),
            vat_total=_money("18.00"),
            grand_total=_money("118.00"),
        )
        s = compute_field_confidence(c)
        assert s["subtotal_total.amount"] == PERFECT
        assert s["vat_total.amount"] == PERFECT
        assert s["grand_total.amount"] == PERFECT

    def test_missing_subtotal_does_not_fail_cross_check(self):
        c = _full_invoice(
            subtotal_total=None,
            vat_total=_money("441.00"),
            grand_total=_money("2891.00"),
        )
        s = compute_field_confidence(c)
        assert s["subtotal_total.amount"] == MISSING
        # No cross-check fails when an operand is missing.
        assert s["grand_total.amount"] == PERFECT

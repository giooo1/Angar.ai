"""Per-field confidence heuristic for extracted CanonicalInvoice (WS2).

The Anthropic SDK doesn't return per-field confidence — the model just
gives us a JSON object. To populate the new Review v2 screen's
confidence cues with something honest, we compute a lightweight score
in [0, 1] per field by mixing four signals:

  1.0   present, matches expected format, all cross-checks pass
  0.85  present, format mismatch but plausible (e.g. TIN without GE prefix)
  0.70  present, fails a cross-check (e.g. subtotal + VAT ≠ grand_total)
  0.40  present but suspicious (empty / whitespace / "N/A")
  0.0   null or missing

The frontend bins:  ≥0.85 high · 0.60–0.84 med · <0.60 low

This module is a pure function over CanonicalInvoice → dict. No DB, no
side effects. Called from `extraction_service.run_extraction` on the
success branch and stored as `Extraction.field_confidence`.
"""

from __future__ import annotations

import re
from datetime import date
from decimal import Decimal
from typing import Any

from angar_schema.canonical import CanonicalInvoice, Currency

# ---------------------------------------------------------------------------
# Score levels
# ---------------------------------------------------------------------------

PERFECT = 1.0
FORMAT_OFF = 0.85
CROSS_CHECK_FAIL = 0.70
SUSPICIOUS = 0.40
MISSING = 0.0

# ---------------------------------------------------------------------------
# Format regexes
# ---------------------------------------------------------------------------

# Georgian TIN: 9 digits, optionally prefixed by 'GE' and/or separated
# by spaces. We accept either form because the model strips spaces but
# sometimes keeps the GE prefix.
_TIN_RE = re.compile(r"^(?:GE)?\s*\d{3}\s*\d{3}\s*\d{3}$", re.IGNORECASE)

# Strings the model sometimes emits when it would otherwise be null.
_SUSPICIOUS = {"", "n/a", "na", "none", "null", "unknown", "-", "—"}


def _is_suspicious(text: str | None) -> bool:
    return text is None or text.strip().lower() in _SUSPICIOUS


def _score_string(
    value: str | None,
    *,
    format_re: re.Pattern[str] | None = None,
) -> float:
    if value is None:
        return MISSING
    stripped = value.strip()
    if not stripped or stripped.lower() in _SUSPICIOUS:
        return SUSPICIOUS
    if format_re is not None and not format_re.match(stripped):
        return FORMAT_OFF
    return PERFECT


def _score_date(value: date | None) -> float:
    # Pydantic validates `date`-typed fields up front, so a non-null
    # value here is guaranteed to be a parseable calendar date — no
    # format check needed beyond presence.
    return PERFECT if value is not None else MISSING


def _score_amount(amount: Decimal | None) -> float:
    if amount is None:
        return MISSING
    # Zero is a real value (free-of-charge / waybills); don't punish it.
    return PERFECT


def _cross_check_totals(canonical: CanonicalInvoice) -> bool:
    """Return True iff subtotal + vat - discount + shipping ≈ grand_total
    (within 0.01). If any operand is missing, fall back to True (no fail)."""
    grand = canonical.grand_total
    if grand is None:
        return True
    subtotal = canonical.subtotal_total
    vat = canonical.vat_total
    if subtotal is None or vat is None:
        return True
    expected = subtotal.amount + vat.amount
    if canonical.discount_total is not None:
        expected -= canonical.discount_total.amount
    if canonical.shipping_cost is not None:
        expected += canonical.shipping_cost.amount
    return abs(expected - grand.amount) <= Decimal("0.01")


def compute_field_confidence(canonical: CanonicalInvoice) -> dict[str, float]:
    """Score every UI-rendered field. Keys mirror the dotted paths the
    Review v2 frontend uses to look them up.
    """
    out: dict[str, float] = {}

    # --- Seller ---
    seller = canonical.seller
    if seller is None:
        for key in ("seller.name", "seller.tin", "seller.party_type", "seller.address"):
            out[key] = MISSING
    else:
        out["seller.name"] = _score_string(seller.name)
        out["seller.tin"] = (
            _score_string(seller.tin, format_re=_TIN_RE) if seller.tin else MISSING
        )
        out["seller.party_type"] = (
            PERFECT if seller.party_type.value != "unknown" else SUSPICIOUS
        )
        out["seller.address"] = _score_string(seller.address)

    # --- Buyer ---
    buyer = canonical.buyer
    if buyer is None:
        for key in ("buyer.name", "buyer.tin", "buyer.party_type", "buyer.address"):
            out[key] = MISSING
    else:
        out["buyer.name"] = _score_string(buyer.name)
        out["buyer.tin"] = (
            _score_string(buyer.tin, format_re=_TIN_RE) if buyer.tin else MISSING
        )
        out["buyer.party_type"] = (
            PERFECT if buyer.party_type.value != "unknown" else SUSPICIOUS
        )
        out["buyer.address"] = _score_string(buyer.address)

    # --- Document ---
    out["document_number"] = _score_string(canonical.document_number)
    out["document_date"] = _score_date(canonical.document_date)
    out["document_currency"] = (
        PERFECT
        if canonical.document_currency != Currency.UNKNOWN
        else SUSPICIOUS
    )

    # --- Amounts (with cross-check) ---
    totals_ok = _cross_check_totals(canonical)

    def _amount_score(money_field: Any) -> float:
        if money_field is None:
            return MISSING
        base = _score_amount(money_field.amount)
        if base != PERFECT:
            return base
        return PERFECT if totals_ok else CROSS_CHECK_FAIL

    out["subtotal_total.amount"] = _amount_score(canonical.subtotal_total)
    out["vat_total.amount"] = _amount_score(canonical.vat_total)
    out["grand_total.amount"] = _amount_score(canonical.grand_total)

    # --- Line items ---
    out["items"] = PERFECT if canonical.items else MISSING

    return out

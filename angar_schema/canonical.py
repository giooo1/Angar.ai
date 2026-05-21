"""
Angar.ai — Canonical Invoice Schema (v0.2)
============================================

Changes from v0.1, derived from hand-labeling 8 real Georgian documents:

  1. VATTreatment gained NOT_APPLICABLE, INCLUSIVE, and UNKNOWN values
     to reflect B2C, "VAT included" totals, and genuinely-unclear cases.

  2. DocumentType gained PAYMENT_ORDER (Terabank/TBC payment confirmations
     that get uploaded by mistake) and document-level `accepted` field for
     explicit rejection workflows.

  3. LineItem.unit is now Optional — half of real documents don't show units.

  4. New `is_free_of_charge` field at document level for waybills with
     უსასყიდლოდ (no money owed but declared value present).

  5. New `references_other_document` field for payment orders pointing to
     the invoice they pay (e.g., "ინვოისი 0496").

  6. New `extraction_notes` list at document level for AI-surfaced warnings
     ("VAT-inclusive total", "stacked prices in one cell", etc.).

  7. New script-tracking on Party so we can capture mixed-script documents
     where seller is transliterated and buyer is Mkhedruli.

  8. Party.tin_label_present: distinguishes a labeled TIN (trustworthy) from
     a 9-digit-number-found-on-the-page (phone-number-as-TIN trap).

Seller/buyer naming kept per user decision: stays close to RS.ge and Oris
conventions, relies on null for documents that don't fit cleanly.

This is v0.2. Still draft. Will change after the first extraction run
reveals what the AI actually produces vs. what we asked for.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class Currency(str, Enum):
    GEL = "GEL"
    USD = "USD"
    EUR = "EUR"
    RUB = "RUB"
    TRY = "TRY"
    OTHER = "OTHER"
    UNKNOWN = "UNKNOWN"  # Some docs simply don't state currency


class DocumentType(str, Enum):
    """Top-level classification.

    PAYMENT_ORDER is included specifically so the agent can REJECT these
    documents cleanly rather than mis-extracting them as invoices.
    """
    VAT_INVOICE = "vat_invoice"
    REGULAR_INVOICE = "regular_invoice"      # ინვოისი, no VAT line
    WAYBILL = "waybill"
    RECEIPT = "receipt"
    UTILITY_BILL = "utility_bill"
    PAYMENT_ORDER = "payment_order"          # NOT an invoice — reject
    UNKNOWN = "unknown"


class VATTreatment(str, Enum):
    """How VAT applies. Expanded from v0.1 based on real documents.

    NOT_APPLICABLE: document explicitly says "No taxes" — typically B2C
    INCLUSIVE: total is VAT-inclusive, no breakdown ("დღგ-ს ჩათვლით")
    UNKNOWN: document has no VAT info and we genuinely don't know why
    """
    STANDARD = "standard"
    ZERO_RATED = "zero_rated"
    EXEMPT = "exempt"
    REVERSE_CHARGE = "reverse_charge"
    NOT_APPLICABLE = "not_applicable"
    INCLUSIVE = "inclusive"
    UNKNOWN = "unknown"


class PartyType(str, Enum):
    LEGAL_ENTITY = "legal_entity"
    INDIVIDUAL_GE = "individual_ge"
    FOREIGN_PERSON = "foreign_person"
    UNKNOWN = "unknown"


class Script(str, Enum):
    """Script used for a string field.

    Critical because invoice_005 showed that seller and buyer can be in
    different scripts within the same document.
    """
    MKHEDRULI = "mkhedruli"
    LATIN = "latin"
    LATIN_TRANSLITERATED_GEORGIAN = "latin_transliterated_georgian"
    MIXED = "mixed"
    UNKNOWN = "unknown"


# ---------------------------------------------------------------------------
# Sub-models
# ---------------------------------------------------------------------------

class Money(BaseModel):
    """An amount with explicit currency."""
    amount: Decimal
    currency: Currency

    model_config = ConfigDict(frozen=True)


class Party(BaseModel):
    """A named party on the document.

    Used for both seller/buyer on invoices and shipper/recipient on waybills.
    The document_type and party role disambiguate semantics.
    """

    name: str = Field(..., description="Name as written, verbatim")

    tin: Optional[str] = Field(
        None,
        description="Taxpayer ID, ONLY if explicitly labeled on document. "
                    "Strip whitespace ('205 025 676' -> '205025676'). "
                    "Do NOT fill from unlabeled 9-digit numbers (phone-number trap).",
    )

    tin_label_present: bool = Field(
        default=False,
        description="True if the document explicitly labeled the TIN "
                    "(`saidentipikacio kodi`, `s/k`, `Tax ID`). "
                    "Distinguishes trustworthy TINs from numeric coincidences.",
    )

    party_type: PartyType = PartyType.UNKNOWN

    address: Optional[str] = None
    bank_account: Optional[str] = Field(
        None,
        description="IBAN, whitespace-stripped.",
    )

    script: Script = Script.UNKNOWN
    extracted_from_region: Optional[str] = None


class LineItem(BaseModel):
    """A single line on the document.

    Many fields are now Optional based on what real documents actually
    contain. unit_price and quantity remain required when a line exists.
    """

    description: str = Field(..., description="Item or service name")
    quantity: Decimal
    unit: Optional[str] = Field(
        None,
        description="Unit as written. Optional - many B2C documents have no unit column.",
    )

    unit_price: Money
    subtotal: Optional[Money] = Field(
        None,
        description="quantity * unit_price, before VAT, if shown on doc.",
    )
    vat_amount: Optional[Money] = Field(
        None,
        description="Per-line VAT, if shown. Often only document-level.",
    )
    total: Money

    vat_treatment: VATTreatment = VATTreatment.UNKNOWN

    sku: Optional[str] = None
    barcode: Optional[str] = None
    item_code: Optional[str] = None

    excise_amount: Optional[Money] = None
    excise_code: Optional[str] = None

    # Sub-items captured here when a row visually packs multiple
    # charges into one cell (invoice_007: 455.00 / 200.00 stacked).
    sub_charges: list[Money] = Field(
        default_factory=list,
        description="When one row contains multiple price components "
                    "stacked in a single cell, list them here.",
    )


class TransportInfo(BaseModel):
    """Transport details - required for waybills, absent on most invoices."""

    start_address: Optional[str] = None
    end_address: Optional[str] = None
    driver: Optional[Party] = None

    vehicle_plate: Optional[str] = Field(
        None,
        description="Georgian plate format AANNNAA (letters-digits-letters, "
                    "no separators). e.g. 'UN712UU'.",
    )
    has_trailer: Optional[bool] = None
    transport_cost: Optional[Money] = None
    transport_cost_payer: Optional[str] = Field(
        None,
        description="'seller' or 'buyer' - who pays for transport.",
    )
    begin_date: Optional[datetime] = None
    delivery_date: Optional[datetime] = None


class ExtractionMetadata(BaseModel):
    """Audit trail for the extraction itself."""

    source_filename: str
    source_pdf_sha256: str
    extracted_at: datetime
    model_version: str
    prompt_version: str

    field_confidence: dict[str, float] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    processing_time_ms: Optional[int] = None


# ---------------------------------------------------------------------------
# The canonical document
# ---------------------------------------------------------------------------

class CanonicalInvoice(BaseModel):
    """Canonical extracted form of a Georgian invoice or waybill.

    The schema also accommodates documents that *should* be rejected - we
    classify them, set accepted=False, and use the rejection_reason field
    rather than returning a separate error type. This keeps the eval harness
    simple: one shape in, one shape out.
    """

    # === Acceptance gate ===
    accepted: bool = Field(
        ...,
        description="True if this document is extractable as an invoice/waybill. "
                    "False for payment orders, statements, quotes, etc.",
    )
    rejection_reason: Optional[str] = Field(
        None,
        description="If accepted=False, why.",
    )

    # === Document identity ===
    document_type: DocumentType
    document_number: Optional[str] = None
    document_date: Optional[date] = None
    document_currency: Currency = Currency.UNKNOWN

    # === Parties ===
    # Both Optional because rejected documents (payment orders) don't have
    # seller/buyer in the invoice sense. We capture sender/receiver info
    # in extraction_notes for downstream pairing.
    seller: Optional[Party] = None
    buyer: Optional[Party] = None

    # === Line items ===
    items: list[LineItem] = Field(default_factory=list)

    # === Totals ===
    subtotal_total: Optional[Money] = None
    vat_total: Optional[Money] = None
    discount_total: Optional[Money] = None
    shipping_cost: Optional[Money] = None
    grand_total: Optional[Money] = None

    # === VAT / tax flags ===
    is_vat_invoice: bool = False
    is_reverse_vat: bool = False
    vat_treatment_overall: VATTreatment = VATTreatment.UNKNOWN
    vat_treatment_reason: Optional[str] = Field(
        None,
        description="Free-text rationale, e.g. 'B2C consumer sale', "
                    "'Medical service exempt under Georgian tax code'.",
    )

    # === Free-of-charge waybills (Waybill_List case) ===
    is_free_of_charge: bool = Field(
        default=False,
        description="True when document shows usasq'idlod / 'free of charge'. "
                    "Listed totals are DECLARED VALUE, not money owed.",
    )

    # === Document linkage (payment orders pointing to invoices) ===
    references_other_document: Optional[str] = Field(
        None,
        description="If this document references another (e.g. payment order "
                    "saying 'invoisi 0496'), capture the referenced number here.",
    )

    # === Optional sections ===
    transport: Optional[TransportInfo] = None
    notes: Optional[str] = None

    # === Quality / sensitivity flags ===
    contains_pii_beyond_parties: bool = Field(
        default=False,
        description="True when line items contain personal data beyond "
                    "normal party info - e.g. patient names, medical "
                    "procedures (invoice_007). Triggers redaction in logs.",
    )

    extraction_notes: list[str] = Field(
        default_factory=list,
        description="Free-form notes the AI surfaced about this document.",
    )

    # === Audit trail ===
    extraction: ExtractionMetadata


# ---------------------------------------------------------------------------
# Quick self-test
# ---------------------------------------------------------------------------

def _smoke_test() -> None:
    """Verify the schema can represent each of the labeled document classes."""
    import json

    # Case 1: A rejected payment order (invoice_003)
    rejected = CanonicalInvoice(
        accepted=False,
        rejection_reason="Bank payment order, not an invoice",
        document_type=DocumentType.PAYMENT_ORDER,
        document_number="6509299",
        document_date=date(2024, 11, 14),
        document_currency=Currency.GEL,
        grand_total=Money(amount=Decimal("200.00"), currency=Currency.GEL),
        extraction_notes=[
            "Sender: sopio gakharia (p/n 01001079750)",
            "Receiver: Tbilisi State Medical University",
            "Operation: tuition payment",
        ],
        extraction=ExtractionMetadata(
            source_filename="invoice_003.pdf",
            source_pdf_sha256="abc",
            extracted_at=datetime.now(),
            model_version="claude-opus-4-7",
            prompt_version="v0.2",
        ),
    )

    # Case 2: B2C invoice with no VAT and document-level discount (invoice_001)
    b2c = CanonicalInvoice(
        accepted=True,
        document_type=DocumentType.REGULAR_INVOICE,
        document_number="IN234454",
        document_date=date(2025, 5, 19),
        document_currency=Currency.GEL,
        seller=Party(
            name="DRESSUP.GE",
            tin=None,
            tin_label_present=False,
            party_type=PartyType.UNKNOWN,
            script=Script.LATIN,
        ),
        buyer=Party(
            name="Giorgi Gakharia",
            tin=None,
            tin_label_present=False,
            party_type=PartyType.UNKNOWN,
            script=Script.MIXED,
        ),
        items=[
            LineItem(
                description="CALVIN KLEIN JEANS",
                quantity=Decimal("1"),
                unit=None,
                unit_price=Money(amount=Decimal("219.00"), currency=Currency.GEL),
                total=Money(amount=Decimal("219.00"), currency=Currency.GEL),
                vat_treatment=VATTreatment.NOT_APPLICABLE,
                sku="J30J324814 1A4",
            ),
        ],
        subtotal_total=Money(amount=Decimal("896.00"), currency=Currency.GEL),
        discount_total=Money(amount=Decimal("179.20"), currency=Currency.GEL),
        shipping_cost=Money(amount=Decimal("5.95"), currency=Currency.GEL),
        grand_total=Money(amount=Decimal("722.75"), currency=Currency.GEL),
        is_vat_invoice=False,
        vat_treatment_overall=VATTreatment.NOT_APPLICABLE,
        vat_treatment_reason="B2C consumer sale",
        extraction_notes=[
            "9-digit number 557115503 under buyer address is a phone number, not a TIN",
            "Discount applied at document level, not per line",
        ],
        extraction=ExtractionMetadata(
            source_filename="invoice_001.pdf",
            source_pdf_sha256="def",
            extracted_at=datetime.now(),
            model_version="claude-opus-4-7",
            prompt_version="v0.2",
        ),
    )

    # Case 3: Free-of-charge waybill (Waybill_List)
    waybill = CanonicalInvoice(
        accepted=True,
        document_type=DocumentType.WAYBILL,
        document_number="el-0976696987",
        document_date=date(2026, 5, 7),
        document_currency=Currency.GEL,
        seller=Party(
            name="Vita Sana LLC",
            tin="404663486",
            tin_label_present=True,
            party_type=PartyType.LEGAL_ENTITY,
            script=Script.MKHEDRULI,
        ),
        buyer=Party(
            name="Imedi Clinic LLC",
            tin="202249110",
            tin_label_present=True,
            party_type=PartyType.LEGAL_ENTITY,
            script=Script.MKHEDRULI,
        ),
        items=[
            LineItem(
                description="Latex gloves, non-sterile, powder-free, size M",
                quantity=Decimal("1000.0000"),
                unit="pair",
                unit_price=Money(amount=Decimal("0.0900"), currency=Currency.GEL),
                total=Money(amount=Decimal("90.0000"), currency=Currency.GEL),
                vat_treatment=VATTreatment.UNKNOWN,
                item_code="1753766950250874-TaiyuGloves23072025-20270131",
            ),
        ],
        grand_total=Money(amount=Decimal("90.0000"), currency=Currency.GEL),
        is_free_of_charge=True,
        transport=TransportInfo(
            start_address="Tbilisi, Lilo, Giorgi Chikvaidze 4",
            end_address="Tbilisi, Vake-Saburtalo, Vepkhistq'aosanis 38",
            driver=Party(
                name="Otari Ejibia",
                tin="39001010508",
                tin_label_present=True,
                party_type=PartyType.INDIVIDUAL_GE,
                script=Script.MKHEDRULI,
            ),
            vehicle_plate="UN712UU",
            begin_date=datetime(2026, 5, 7, 12, 25, 50),
        ),
        extraction_notes=[
            "Free of charge - total is declared value, not amount owed",
            "Numeric precision 4 decimal places (waybills, vs 2 for invoices)",
            "Driver TIN is 11-digit personal ID",
        ],
        extraction=ExtractionMetadata(
            source_filename="Waybill_List.pdf",
            source_pdf_sha256="ghi",
            extracted_at=datetime.now(),
            model_version="claude-opus-4-7",
            prompt_version="v0.2",
        ),
    )

    for label, doc in [
        ("rejected payment order", rejected),
        ("B2C invoice", b2c),
        ("free waybill", waybill),
    ]:
        s = doc.model_dump(mode="json")
        assert s["accepted"] in (True, False)
        print(f"OK: {label} serializes cleanly ({len(json.dumps(s))} bytes)")


if __name__ == "__main__":
    _smoke_test()

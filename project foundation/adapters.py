"""
Angar.ai — Adapter Sketches (v0.1 draft)
=========================================

Four adapters that read from CanonicalInvoice and produce output for each
downstream system. These are sketches, not finished code — the goal is
to make the mappings visible and reviewable on paper before committing to
implementation.

Adapters share a common shape:

    class XXXAdapter:
        def to_xxx(self, doc: CanonicalInvoice) -> XXXOutput: ...

They never mutate the input. They never call the network themselves —
they produce serialized output (XML string, JSON dict, .xlsx bytes) which
a separate transport layer hands off to the actual API.

Why? Pure functions are testable in isolation. The eval harness can
compare adapter output against fixtures without touching the network.

KNOWN UNKNOWNS — see each adapter's docstring for fields that need
verification against real responses.
"""

from __future__ import annotations

from decimal import Decimal
from datetime import datetime
from typing import Any

from lxml import etree

# Assume the canonical module is importable
from canonical import (
    CanonicalInvoice,
    LineItem,
    Party,
    PartyType,
    VATTreatment,
    Currency,
    DocumentType,
)


# ===========================================================================
# Adapter 1 — RS.ge Waybill XML
# ===========================================================================
#
# Produces the <WAYBILL> XML structure that save_waybill expects.
# Verified working on the test environment last night.
#
# CRITICAL CONSTRAINTS DISCOVERED IN TESTING:
#   - DRIVER_TIN is REQUIRED for transport-type waybills (error -1012)
#   - CHEK_DRIVER_TIN must be 1 for 11-digit Georgian personal IDs
#   - CAR_NUMBER must match Georgian plate format AA001AA (error -1026)
#   - SELER_UN_ID is the seller's internal Oris-like ID, NOT their TIN
#     → must be looked up via get_service_users once per customer onboarding
#
# UNIT_ID, TYPE, etc. are reference-dictionary IDs from RS.ge; the adapter
# resolves them via lookup tables built from get_waybill_units etc.
#
class RSGEWaybillAdapter:
    """Canonical → RS.ge waybill XML."""

    # Hardcoded reference IDs we've already looked up from RS.ge.
    # In production these come from the cached reference tables, not constants.
    WAYBILL_TYPE_DELIVERY = 2          # მიწოდება ტრანსპორტირებით
    DEFAULT_TRANSPORT_TYPE = 1         # სატვირთო მანქანა
    DEFAULT_TRANSPORT_COST_PAYER = 1   # 1 = buyer pays

    # Unit name → RS.ge UNIT_ID mapping
    # Populated from get_waybill_units once per environment
    UNIT_MAP: dict[str, int] = {
        "ცალი": 1,
        "კგ": 2,
        "ლიტრი": 3,
        # ... etc; populate from real reference dict
    }

    def __init__(self, seller_un_id: int):
        """seller_un_id is fetched once during customer onboarding via
        get_service_users, then cached per customer."""
        self.seller_un_id = seller_un_id

    def to_xml(self, doc: CanonicalInvoice) -> etree._Element:
        if doc.document_type not in (DocumentType.WAYBILL, DocumentType.VAT_INVOICE):
            raise ValueError(
                f"RS.ge waybill adapter only handles waybills and VAT invoices, "
                f"got {doc.document_type}"
            )

        root = etree.Element("WAYBILL")
        etree.SubElement(root, "SUB_WAYBILLS")

        # --- Goods ---
        goods_list = etree.SubElement(root, "GOODS_LIST")
        for item in doc.items:
            self._append_goods(goods_list, item)

        etree.SubElement(root, "WOOD_DOCS_LIST")  # Empty unless timber waybill

        # --- Header fields ---
        etree.SubElement(root, "ID").text = "0"  # 0 = create new
        etree.SubElement(root, "TYPE").text = str(self.WAYBILL_TYPE_DELIVERY)

        etree.SubElement(root, "BUYER_TIN").text = doc.buyer.tin or ""
        etree.SubElement(root, "CHEK_BUYER_TIN").text = self._chek_tin(doc.buyer)
        etree.SubElement(root, "BUYER_NAME").text = doc.buyer.name

        transport = doc.transport
        etree.SubElement(root, "START_ADDRESS").text = (
            transport.start_address if transport else doc.seller.address or "—"
        )
        etree.SubElement(root, "END_ADDRESS").text = (
            transport.end_address if transport else doc.buyer.address or "—"
        )

        # Driver — REQUIRED for transport waybills
        driver = transport.driver if transport else None
        etree.SubElement(root, "DRIVER_TIN").text = (driver.tin if driver else "") or ""
        etree.SubElement(root, "CHEK_DRIVER_TIN").text = (
            self._chek_tin(driver) if driver else "0"
        )
        etree.SubElement(root, "DRIVER_NAME").text = driver.name if driver else ""

        # Money
        etree.SubElement(root, "TRANSPORT_COAST").text = (
            str(transport.transport_cost.amount) if transport and transport.transport_cost else "0"
        )
        etree.SubElement(root, "FULL_AMOUNT").text = str(doc.grand_total.amount)

        # Misc
        etree.SubElement(root, "STATUS").text = "0"  # 0 = saved (not activated)
        etree.SubElement(root, "SELER_UN_ID").text = str(self.seller_un_id)
        etree.SubElement(root, "PAR_ID").text = ""

        etree.SubElement(root, "CAR_NUMBER").text = (
            transport.vehicle_plate if transport and transport.vehicle_plate else ""
        )

        begin = (transport.begin_date if transport and transport.begin_date else datetime.now())
        etree.SubElement(root, "BEGIN_DATE").text = begin.strftime("%Y-%m-%dT%H:%M:%S")

        etree.SubElement(root, "TRAN_COST_PAYER").text = str(self.DEFAULT_TRANSPORT_COST_PAYER)
        etree.SubElement(root, "TRANS_ID").text = str(self.DEFAULT_TRANSPORT_TYPE)
        etree.SubElement(root, "TRANS_TXT").text = ""

        etree.SubElement(root, "COMMENT").text = doc.notes or ""
        etree.SubElement(root, "CATEGORY").text = "0"  # 0 = ordinary; 1 = timber
        etree.SubElement(root, "IS_MED").text = "0"

        return root

    def _append_goods(self, parent: etree._Element, item: LineItem) -> None:
        node = etree.SubElement(parent, "GOODS")
        etree.SubElement(node, "ID").text = "0"
        etree.SubElement(node, "W_NAME").text = item.description
        etree.SubElement(node, "UNIT_ID").text = str(self._unit_id(item.unit))
        etree.SubElement(node, "QUANTITY").text = str(item.quantity)
        etree.SubElement(node, "PRICE").text = str(item.unit_price.amount)
        etree.SubElement(node, "AMOUNT").text = str(item.subtotal.amount)
        etree.SubElement(node, "BAR_CODE").text = item.barcode or item.sku or ""
        etree.SubElement(node, "A_ID").text = "0"  # No excise for now
        etree.SubElement(node, "STATUS").text = "1"  # Active line
        etree.SubElement(node, "VAT_TYPE").text = str(self._vat_code(item.vat_treatment))

    def _unit_id(self, unit_text: str) -> int:
        return self.UNIT_MAP.get(unit_text.strip(), 99)  # 99 = "other"

    def _vat_code(self, treatment: VATTreatment) -> int:
        return {
            VATTreatment.STANDARD: 0,
            VATTreatment.ZERO_RATED: 1,
            VATTreatment.EXEMPT: 2,
            VATTreatment.REVERSE_CHARGE: 0,  # handled at document level, not line
        }[treatment]

    def _chek_tin(self, party: Party) -> str:
        """The famous CHEK_TIN field. Semantics are:
          - 0 = foreign person OR 9-digit legal entity (legacy quirk)
          - 1 = 11-digit Georgian personal ID
        Discovered through trial-and-error; not in the protocol PDF.
        """
        if party.party_type == PartyType.INDIVIDUAL_GE:
            return "1"
        return "0"


# ===========================================================================
# Adapter 2 — RS.ge VAT Invoice (save_invoice + save_invoice_desc)
# ===========================================================================
#
# UNVERIFIED. We have the protocol PDF but have not yet made a successful
# save_invoice call. The signature here is provisional.
#
# UN_IDs (seller_un_id, buyer_un_id) need to be resolved separately for
# both parties — buyer lookup via get_un_id_from_tin.
#
class RSGEInvoiceAdapter:
    """Canonical → RS.ge VAT invoice (save_invoice + save_invoice_desc).

    Unlike the waybill adapter, this produces a sequence of separate API
    calls rather than one XML document:
      1. save_invoice(...)  → returns new invois_id
      2. save_invoice_desc(...) × N — once per line item
      3. change_invoice_status(status=1)  → send to buyer
    """

    def to_save_invoice_args(
        self,
        doc: CanonicalInvoice,
        seller_un_id: int,
        buyer_un_id: int,
        user_id: int,
    ) -> dict[str, Any]:
        """Build kwargs for the save_invoice call.

        seller_un_id, buyer_un_id, and user_id must be resolved by the caller
        BEFORE this adapter runs — they're not on the canonical document.
        """
        return {
            "user_id": user_id,
            "invois_id": 0,  # 0 = create new
            "operation_date": datetime.combine(doc.document_date, datetime.min.time()),
            "seller_un_id": seller_un_id,
            "buyer_un_id": buyer_un_id,
            "overhead_no": "",   # deprecated per PDF, pass empty
            "overhead_dt": datetime.now(),  # deprecated, value ignored
            "b_s_user_id": 0,
            # 'note' field if using save_invoice_n
            "note": doc.notes or "",
        }

    def to_line_item_args(
        self,
        item: LineItem,
        invois_id: int,
        user_id: int,
    ) -> dict[str, Any]:
        """Build kwargs for one save_invoice_desc call."""
        # drg_amount semantics per protocol PDF:
        #   numeric value > 0 → standard VAT
        #   0 → zero-rated
        #   -1 → exempt
        drg_amount = self._drg_amount(item)

        return {
            "user_id": user_id,
            "id": 0,  # 0 = create new
            "invois_id": invois_id,
            "goods": item.description,
            "g_unit": item.unit,
            "g_number": item.quantity,
            "full_amount": item.total.amount,
            "drg_amount": drg_amount,
            "aqcizi_amount": (
                item.excise_amount.amount if item.excise_amount else Decimal("0")
            ),
            "akciz_id": 0,  # would need lookup if exciseable
        }

    def _drg_amount(self, item: LineItem) -> Decimal:
        if item.vat_treatment == VATTreatment.STANDARD:
            return item.vat_amount.amount
        if item.vat_treatment == VATTreatment.ZERO_RATED:
            return Decimal("0")
        if item.vat_treatment == VATTreatment.EXEMPT:
            return Decimal("-1")
        # REVERSE_CHARGE is unusual at line-item level; default to standard
        return item.vat_amount.amount


# ===========================================================================
# Adapter 3 — Oris JSON API (AcceptOperation)
# ===========================================================================
#
# UNVERIFIED. No live Oris test environment yet. Field names from the
# official API doc, mapping is best-effort.
#
# AcceptOperation = incoming invoice (we received goods from a supplier).
# For outgoing invoices (we sold goods) the equivalent is SupplyOperation
# — same shape, mirrored party direction.
#
# The token must be obtained beforehand via POST /api/LogIn.
# Each customer has their own token (per-database).
#
class OrisAPIAdapter:
    """Canonical → Oris AcceptOperation JSON payload."""

    def to_accept_operation(
        self,
        doc: CanonicalInvoice,
        token: str,
        supplier_id: int,
        rs_vat_number: str | None = None,
        rs_waybill_number: str | None = None,
    ) -> dict[str, Any]:
        """Build the JSON body for POST /api/AcceptOperation.

        supplier_id must be resolved by the caller (via DebitorCreditorsList).
        rs_vat_number / rs_waybill_number link this Oris record to the RS.ge
        documents we already created — this is the bookkeeper's killer feature.
        """
        return {
            "token": token,
            "documentDate": doc.document_date.isoformat(),
            "documentNumber": doc.document_number or "",
            "documentComment": doc.notes or "",
            "currency": doc.document_currency.value,
            "supplierID": supplier_id,
            "createAccountingEntries": True,

            # The cross-system linkage that makes this product valuable
            "rS_VAT_Number": rs_vat_number or "",
            "rS_Waybill_Number": rs_waybill_number or "",

            "acceptOperationItems": [
                self._line_item(item) for item in doc.items
            ],
            "acceptOperationInvoiceExpensesSharingItems": [],
        }

    def _line_item(self, item: LineItem) -> dict[str, Any]:
        return {
            "supplierItemName": item.description,
            "supplierItemCode": item.sku or item.barcode or "",
            "supplierItemUnit": item.unit,
            "quantity": float(item.quantity),  # Oris uses number, not Decimal
            "unit": item.unit,
            "price": float(item.unit_price.amount),
            "amount": float(item.subtotal.amount),
            "vat": float(item.vat_amount.amount),
            "vatRate": float(self._vat_rate(item)),
            "supplierItemVATType": self._vat_type(item.vat_treatment),
            "excise": float(item.excise_amount.amount) if item.excise_amount else 0.0,
        }

    def _vat_rate(self, item: LineItem) -> Decimal:
        if item.subtotal.amount == 0:
            return Decimal("0")
        return (item.vat_amount.amount / item.subtotal.amount) * 100

    def _vat_type(self, treatment: VATTreatment) -> int:
        return {
            VATTreatment.STANDARD: 0,
            VATTreatment.ZERO_RATED: 1,
            VATTreatment.EXEMPT: 2,
            VATTreatment.REVERSE_CHARGE: 0,
        }[treatment]


# ===========================================================================
# Adapter 4 — Oris Excel template (user-mapped columns)
# ===========================================================================
#
# This is the broad-market adapter: works for ALL Oris users, not just
# ones who paid for the API module.
#
# Customer flow:
#   1. Customer uploads their own .xlsx template once (during setup)
#   2. They map "their column X → canonical field Y" in a UI
#   3. The mapping is saved as an OrisTemplateProfile per customer
#   4. For each invoice, the adapter fills the customer's template
#      using their saved mapping
#
# The point: we conform to the customer's existing template, not the
# other way around. This handles the reality that every accountant has
# tweaked their Oris template differently.
#
from dataclasses import dataclass


@dataclass(frozen=True)
class ColumnMapping:
    """One mapping rule: an Excel column header → a canonical field path.

    `column_header` is the actual header text from the customer's template.
    `canonical_path` is a dotted accessor like 'seller.tin' or
    'items[*].description'. The '[*]' marker means 'one row per item'.
    `transform` is an optional callable to format the value (e.g. date format).
    """
    column_header: str
    canonical_path: str
    transform: str | None = None  # e.g. 'date:dd.mm.yyyy', 'currency:GEL', etc.


@dataclass
class OrisTemplateProfile:
    """A customer's saved mapping for their specific Oris template."""
    customer_id: str
    profile_name: str
    template_file_sha256: str
    column_mappings: list[ColumnMapping]
    static_columns: dict[str, Any]  # columns with fixed values
    notes: str | None = None


class OrisExcelAdapter:
    """Canonical → filled-out Excel file matching the customer's template.

    Pseudocode only; real implementation uses openpyxl.
    """

    def __init__(self, profile: OrisTemplateProfile):
        self.profile = profile

    def fill_template(
        self,
        doc: CanonicalInvoice,
        template_bytes: bytes,
    ) -> bytes:
        """Open the customer's template, fill it, return the new file bytes.

        Pseudocode:
          1. Load template_bytes into an openpyxl Workbook
          2. Locate the row where data should start (usually row 2)
          3. For each line item in doc.items:
             a. For each column_mapping in self.profile.column_mappings:
                - Resolve canonical_path against the document
                - Apply transform if present
                - Write to the cell at (data_row, column_index_of(header))
             b. Apply static_columns values
             c. Advance to next row
          4. Return the modified workbook as bytes
        """
        raise NotImplementedError("Sketch only — implement in Phase 4")

    def _resolve_path(self, doc: CanonicalInvoice, path: str, item_index: int) -> Any:
        """Resolve dotted paths against the canonical doc.

        Examples:
          'document_number'           → doc.document_number
          'seller.tin'                → doc.seller.tin
          'items[*].description'      → doc.items[item_index].description
          'items[*].total.amount'     → doc.items[item_index].total.amount
        """
        # Real implementation walks the path with getattr / list indexing
        raise NotImplementedError


# ===========================================================================
# Cross-adapter summary table
# ===========================================================================
#
# This is what you'd put in your project docs as the canonical mapping reference.
# It's the same table I sketched in the conversation, now grounded in real fields.

MAPPING_REFERENCE = """
+-------------------------------+-------------------+-------------------+-------------------+----------------------+
| Canonical field               | RS.ge Waybill XML | RS.ge save_invoice| Oris API JSON     | Oris Excel (sample)  |
+-------------------------------+-------------------+-------------------+-------------------+----------------------+
| document_number               | (n/a; RS issues)  | overhead_no       | documentNumber    | "Invoice #" col      |
| document_date                 | BEGIN_DATE        | operation_date    | documentDate      | "Date" col           |
| document_currency             | (always GEL)      | (always GEL)      | currency          | "Currency" col       |
| seller.tin                    | SELER_UN_ID*      | seller_un_id*     | (linked via       | (used in supplier    |
|                               | (*requires lookup)|                   |  supplierID)      |  lookup)             |
| seller.name                   | (implicit; UN_ID) | (implicit)        | (Oris party)      | "Supplier Name"      |
| buyer.tin                     | BUYER_TIN         | buyer_un_id*      | (n/a for inbound) | (n/a)                |
| buyer.name                    | BUYER_NAME        | (implicit)        | (n/a for inbound) | (n/a)                |
| buyer.party_type              | CHEK_BUYER_TIN    | (n/a)             | (n/a)             | (n/a)                |
| items[*].description          | W_NAME            | goods             | supplierItemName  | "Description" col    |
| items[*].quantity             | QUANTITY          | g_number          | quantity          | "Qty" col            |
| items[*].unit                 | UNIT_ID*          | g_unit            | unit              | "Unit" col           |
| items[*].unit_price.amount    | PRICE             | (computed)        | price             | "Price" col          |
| items[*].subtotal.amount      | AMOUNT            | (computed)        | amount            | "Subtotal" col       |
| items[*].vat_amount.amount    | (computed)        | drg_amount        | vat               | "VAT" col            |
| items[*].vat_treatment        | VAT_TYPE          | drg_amount sign   | supplierItemVAT   | "VAT type" col       |
| items[*].excise_amount.amount | (a_id + lookup)   | aqcizi_amount     | excise            | "Excise" col         |
| grand_total.amount            | FULL_AMOUNT       | (computed)        | (computed)        | "Total" col          |
| transport.start_address       | START_ADDRESS     | (n/a)             | (n/a)             | (n/a)                |
| transport.end_address         | END_ADDRESS       | (n/a)             | (n/a)             | (n/a)                |
| transport.driver.name         | DRIVER_NAME       | (n/a)             | (n/a)             | (n/a)                |
| transport.driver.tin          | DRIVER_TIN        | (n/a)             | (n/a)             | (n/a)                |
| transport.vehicle_plate       | CAR_NUMBER        | (n/a)             | (n/a)             | (n/a)                |
| notes                         | COMMENT           | note              | documentComment   | "Notes" col          |
| (link to RS.ge invoice)       | (n/a)             | (n/a)             | rS_VAT_Number     | (n/a)                |
| (link to RS.ge waybill)       | (n/a)             | (n/a)             | rS_Waybill_Number | (n/a)                |
+-------------------------------+-------------------+-------------------+-------------------+----------------------+
"""


if __name__ == "__main__":
    print(MAPPING_REFERENCE)

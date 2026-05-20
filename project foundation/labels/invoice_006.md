# Gold label: invoice_006 (TBC payment order — from `data/labeling_forms/label_invoice_006.md`)

```json
{
  "accepted": false,
  "rejection_reason": "TBC Bank საგადახდო დავალება / Payment Order — bank transfer record, not an invoice.",
  "document_type": "payment_order",
  "document_number": "1614058726",
  "document_date": "2021-02-23",
  "document_currency": "GEL",
  "seller": null,
  "buyer": null,
  "items": [],
  "subtotal_total": null,
  "vat_total": null,
  "discount_total": null,
  "shipping_cost": null,
  "grand_total": { "amount": "165.00", "currency": "GEL" },
  "is_vat_invoice": false,
  "is_reverse_vat": false,
  "vat_treatment_overall": "unknown",
  "vat_treatment_reason": null,
  "is_free_of_charge": false,
  "references_other_document": "0496",
  "transport": null,
  "notes": null,
  "contains_pii_beyond_parties": false,
  "extraction_notes": [
    "Operation details reference ინვოისი 0496 — payment for invoice 0496 (see invoice_004.pdf), not this document's own invoice number",
    "Sender/payer and receiver/payee must not be mapped as invoice seller/buyer"
  ],
  "extraction": {
    "source_filename": "invoice_006.pdf",
    "source_pdf_sha256": "ignored-in-eval",
    "extracted_at": "2025-01-01T00:00:00Z",
    "model_version": "ignored-in-eval",
    "prompt_version": "ignored-in-eval",
    "field_confidence": {},
    "warnings": [],
    "processing_time_ms": null
  }
}
```

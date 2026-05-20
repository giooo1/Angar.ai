# Gold label: invoice_003 (payment order — from `data/labeling_forms/label_invoice_003.md`)

```json
{
  "accepted": false,
  "rejection_reason": "Terabank საგადახდო დავალება / Payment Order — bank transfer record, not an invoice (no seller/line items as a sale).",
  "document_type": "payment_order",
  "document_number": "6509299",
  "document_date": "2024-11-14",
  "document_currency": "GEL",
  "seller": null,
  "buyer": null,
  "items": [],
  "subtotal_total": null,
  "vat_total": null,
  "discount_total": null,
  "shipping_cost": null,
  "grand_total": { "amount": "200.00", "currency": "GEL" },
  "is_vat_invoice": false,
  "is_reverse_vat": false,
  "vat_treatment_overall": "unknown",
  "vat_treatment_reason": null,
  "is_free_of_charge": false,
  "references_other_document": null,
  "transport": null,
  "notes": null,
  "contains_pii_beyond_parties": false,
  "extraction_notes": [
    "Sender: სოფიო გახარია (11-digit personal ID 01001079750, not company TIN)",
    "Receiver: Tbilisi State Medical University (name may truncate in PDF)",
    "Operation detail describes tuition payment, not priced line items"
  ],
  "extraction": {
    "source_filename": "invoice_003.pdf",
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

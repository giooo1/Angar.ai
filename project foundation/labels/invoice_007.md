# Gold label: invoice_007 (medical invoice — from `data/labeling_forms/label_invoice_007.md`)

```json
{
  "accepted": true,
  "rejection_reason": null,
  "document_type": "regular_invoice",
  "document_number": "N 45",
  "document_date": "2026-05-06",
  "document_currency": "GEL",
  "seller": {
    "name": "შპს \"იმედის კლინიკა\"",
    "tin": "202249110",
    "tin_label_present": true,
    "party_type": "legal_entity",
    "address": "ვეფხისტყაოსნის 38, თბილისი",
    "bank_account": "GE10TB1100000011467550",
    "script": "mkhedruli",
    "extracted_from_region": null
  },
  "buyer": {
    "name": "იმედი",
    "tin": null,
    "tin_label_present": false,
    "party_type": "unknown",
    "address": null,
    "bank_account": null,
    "script": "mkhedruli",
    "extracted_from_region": null
  },
  "items": [
    {
      "description": "ჯალიუკლოვა ბახტიგულის შეწყვეტილი ორსულობისა და ექიმის მომსახურების საფასური.",
      "quantity": "1",
      "unit": null,
      "unit_price": { "amount": "455.00", "currency": "GEL" },
      "subtotal": null,
      "vat_amount": null,
      "total": { "amount": "655.00", "currency": "GEL" },
      "vat_treatment": "exempt",
      "sku": null,
      "barcode": null,
      "item_code": null,
      "excise_amount": null,
      "excise_code": null,
      "sub_charges": [
        { "amount": "455.00", "currency": "GEL" },
        { "amount": "200.00", "currency": "GEL" }
      ]
    }
  ],
  "subtotal_total": { "amount": "655.00", "currency": "GEL" },
  "vat_total": null,
  "discount_total": null,
  "shipping_cost": null,
  "grand_total": { "amount": "655.00", "currency": "GEL" },
  "is_vat_invoice": false,
  "is_reverse_vat": false,
  "vat_treatment_overall": "exempt",
  "vat_treatment_reason": "Medical services VAT-exempt under Georgian tax code (no VAT line on document)",
  "is_free_of_charge": false,
  "references_other_document": null,
  "transport": null,
  "notes": null,
  "contains_pii_beyond_parties": true,
  "extraction_notes": [
    "Line item contains patient-identifying text; protect in logs and downstream systems",
    "Two unit prices stacked in one cell (455.00 and 200.00) captured as sub_charges",
    "Waybill-style template fields empty — classify by filled pricing table, not empty transport fields"
  ],
  "extraction": {
    "source_filename": "invoice_007.pdf",
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

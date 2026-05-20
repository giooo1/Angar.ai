# Gold label: invoice_001 (B2C regular invoice, from `data/labeling_forms/label_invoice_001.md`)

Hand label for eval. Paths under `extraction` that are run-specific are ignored when scoring.

```json
{
  "accepted": true,
  "rejection_reason": null,
  "document_type": "regular_invoice",
  "document_number": "IN234454",
  "document_date": "2025-05-19",
  "document_currency": "GEL",
  "seller": {
    "name": "DRESSUP.GE",
    "tin": null,
    "tin_label_present": false,
    "party_type": "unknown",
    "address": null,
    "bank_account": null,
    "script": "latin",
    "extracted_from_region": null
  },
  "buyer": {
    "name": "Giorgi Gakharia",
    "tin": null,
    "tin_label_present": false,
    "party_type": "individual_ge",
    "address": "68a, T'bilisi, Georgia, Tbilisi თბილისი / Tbilisi, საქართველო",
    "bank_account": null,
    "script": "mixed",
    "extracted_from_region": null
  },
  "items": [
    {
      "description": "CALVIN KLEIN JEANS - წელის ზომა : 30- სიგრძე : 30 (ref J30J324814 1A4)",
      "quantity": "1",
      "unit": null,
      "unit_price": { "amount": "219.00", "currency": "GEL" },
      "subtotal": { "amount": "219.00", "currency": "GEL" },
      "vat_amount": null,
      "total": { "amount": "219.00", "currency": "GEL" },
      "vat_treatment": "not_applicable",
      "sku": null,
      "barcode": null,
      "item_code": null,
      "excise_amount": null,
      "excise_code": null,
      "sub_charges": []
    },
    {
      "description": "CALVIN KLEIN JEANS - წელის ზომა : 30- სიგრძე : 32 (ref J30J324188 1AA)",
      "quantity": "1",
      "unit": null,
      "unit_price": { "amount": "219.00", "currency": "GEL" },
      "subtotal": { "amount": "219.00", "currency": "GEL" },
      "vat_amount": null,
      "total": { "amount": "219.00", "currency": "GEL" },
      "vat_treatment": "not_applicable",
      "sku": null,
      "barcode": null,
      "item_code": null,
      "excise_amount": null,
      "excise_code": null,
      "sub_charges": []
    },
    {
      "description": "HUMMEL - HML GIZE - ზომა : 41 (ref 900561-200 1)",
      "quantity": "1",
      "unit": null,
      "unit_price": { "amount": "229.00", "currency": "GEL" },
      "subtotal": { "amount": "229.00", "currency": "GEL" },
      "vat_amount": null,
      "total": { "amount": "229.00", "currency": "GEL" },
      "vat_treatment": "not_applicable",
      "sku": null,
      "barcode": null,
      "item_code": null,
      "excise_amount": null,
      "excise_code": null,
      "sub_charges": []
    },
    {
      "description": "HUMMEL - HML GIZE - ზომა : 42 (ref 900561-200 1)",
      "quantity": "1",
      "unit": null,
      "unit_price": { "amount": "229.00", "currency": "GEL" },
      "subtotal": { "amount": "229.00", "currency": "GEL" },
      "vat_amount": null,
      "total": { "amount": "229.00", "currency": "GEL" },
      "vat_treatment": "not_applicable",
      "sku": null,
      "barcode": null,
      "item_code": null,
      "excise_amount": null,
      "excise_code": null,
      "sub_charges": []
    }
  ],
  "subtotal_total": { "amount": "896.00", "currency": "GEL" },
  "vat_total": null,
  "discount_total": { "amount": "179.20", "currency": "GEL" },
  "shipping_cost": { "amount": "5.95", "currency": "GEL" },
  "grand_total": { "amount": "722.75", "currency": "GEL" },
  "is_vat_invoice": false,
  "is_reverse_vat": false,
  "vat_treatment_overall": "not_applicable",
  "vat_treatment_reason": "B2C consumer sale",
  "is_free_of_charge": false,
  "references_other_document": null,
  "transport": null,
  "notes": null,
  "contains_pii_beyond_parties": false,
  "extraction_notes": [
    "9-digit number 557115503 under buyer address is a phone number, not a TIN",
    "Discount applied at document level, not per line",
    "Regular price column is RRP/MSRP; use the unit price column for charged amounts"
  ],
  "extraction": {
    "source_filename": "invoice_001.pdf",
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

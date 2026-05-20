# Gold label: invoice_004 (from `data/labeling_forms/label_invoice_004.md`)

```json
{
  "accepted": true,
  "rejection_reason": null,
  "document_type": "regular_invoice",
  "document_number": "0496",
  "document_date": "2021-02-22",
  "document_currency": "UNKNOWN",
  "seller": {
    "name": "შპს მულტიტესტი / Multitest LTD",
    "tin": "205025676",
    "tin_label_present": true,
    "party_type": "legal_entity",
    "address": "0126, ქ. თბილისი, სოფ. დიღომი, აღმაშენებლის ქ. №35 (13, Agmashenebeli str. Tbilisi. 0126)",
    "bank_account": null,
    "script": "mkhedruli",
    "extracted_from_region": null
  },
  "buyer": {
    "name": "შ.პ.ს. \"ეიფორია\"",
    "tin": "405358447",
    "tin_label_present": true,
    "party_type": "legal_entity",
    "address": null,
    "bank_account": null,
    "script": "mkhedruli",
    "extracted_from_region": null
  },
  "items": [
    {
      "description": "ეთილის სპირტი",
      "quantity": "1",
      "unit": null,
      "unit_price": { "amount": "15.00", "currency": "GEL" },
      "subtotal": null,
      "vat_amount": null,
      "total": { "amount": "15.00", "currency": "GEL" },
      "vat_treatment": "unknown",
      "sku": null,
      "barcode": null,
      "item_code": null,
      "excise_amount": null,
      "excise_code": null,
      "sub_charges": []
    },
    {
      "description": "ალდეჰიდები, უმაღლესი სპირტები, ეთერები, მეთილის სპირტი",
      "quantity": "1",
      "unit": null,
      "unit_price": { "amount": "150.00", "currency": "GEL" },
      "subtotal": null,
      "vat_amount": null,
      "total": { "amount": "150.00", "currency": "GEL" },
      "vat_treatment": "unknown",
      "sku": null,
      "barcode": null,
      "item_code": null,
      "excise_amount": null,
      "excise_code": null,
      "sub_charges": []
    }
  ],
  "subtotal_total": { "amount": "165.00", "currency": "GEL" },
  "vat_total": null,
  "discount_total": null,
  "shipping_cost": null,
  "grand_total": { "amount": "165.00", "currency": "GEL" },
  "is_vat_invoice": false,
  "is_reverse_vat": false,
  "vat_treatment_overall": "unknown",
  "vat_treatment_reason": "No VAT line; seller likely below VAT-registration threshold",
  "is_free_of_charge": false,
  "references_other_document": null,
  "transport": null,
  "notes": null,
  "contains_pii_beyond_parties": false,
  "extraction_notes": [
    "Currency not printed on document; GEL inferred from context",
    "Service title row is not a line item — only table body rows are line items"
  ],
  "extraction": {
    "source_filename": "invoice_004.pdf",
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

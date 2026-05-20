# Gold label: invoice_005 (from `data/labeling_forms/label_invoice_005.md`)

```json
{
  "accepted": true,
  "rejection_reason": null,
  "document_type": "regular_invoice",
  "document_number": "79",
  "document_date": "2021-05-06",
  "document_currency": "UNKNOWN",
  "seller": {
    "name": "S.p.s. \"Rvinis laboratoria\"",
    "tin": "202330398",
    "tin_label_present": true,
    "party_type": "legal_entity",
    "address": "didi diRmidan gldanSi mimavali gzatkecili nakv.4|60, Tbilisi",
    "bank_account": "GE97TB75287360601000001",
    "script": "latin_transliterated_georgian",
    "extracted_from_region": null
  },
  "buyer": {
    "name": "შპს ეიფორია",
    "tin": null,
    "tin_label_present": false,
    "party_type": "legal_entity",
    "address": null,
    "bank_account": null,
    "script": "mkhedruli",
    "extracted_from_region": null
  },
  "items": [
    {
      "description": "გამოცდის ოქმი ადგილობრივი ბაზრისთვის",
      "quantity": "1",
      "unit": null,
      "unit_price": { "amount": "100.0", "currency": "GEL" },
      "subtotal": null,
      "vat_amount": null,
      "total": { "amount": "100.0", "currency": "GEL" },
      "vat_treatment": "inclusive",
      "sku": null,
      "barcode": null,
      "item_code": null,
      "excise_amount": null,
      "excise_code": null,
      "sub_charges": []
    }
  ],
  "subtotal_total": { "amount": "100.0", "currency": "GEL" },
  "vat_total": null,
  "discount_total": null,
  "shipping_cost": null,
  "grand_total": { "amount": "100.0", "currency": "GEL" },
  "is_vat_invoice": false,
  "is_reverse_vat": false,
  "vat_treatment_overall": "inclusive",
  "vat_treatment_reason": "Document states VAT-inclusive total (დღგ-ს ჩათვლით) but no VAT amount is broken out",
  "is_free_of_charge": false,
  "references_other_document": null,
  "transport": null,
  "notes": null,
  "contains_pii_beyond_parties": false,
  "extraction_notes": [
    "Mixed scripts: seller block Latin-transliterated Georgian, buyer/items Mkhedruli",
    "Currency not stated on document; GEL inferred from domestic context",
    "Invoice number appears as top banner 'ანგარიში 79' while '#' field is blank"
  ],
  "extraction": {
    "source_filename": "invoice_005.pdf",
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

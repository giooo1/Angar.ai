# Gold label: Waybill_List10 (from `data/labeling_forms/label_Waybill_List10.md`)

```json
{
  "accepted": true,
  "rejection_reason": null,
  "document_type": "waybill",
  "document_number": "ელ-0979247726",
  "document_date": "2026-05-19",
  "document_currency": "GEL",
  "seller": {
    "name": "სატესტო კოდი1",
    "tin": "206322102",
    "tin_label_present": true,
    "party_type": "legal_entity",
    "address": null,
    "bank_account": null,
    "script": "mkhedruli",
    "extracted_from_region": null
  },
  "buyer": {
    "name": "სატესტოk სატესტოk",
    "tin": "12345678910",
    "tin_label_present": true,
    "party_type": "individual_ge",
    "address": null,
    "bank_account": null,
    "script": "mixed",
    "extracted_from_region": null
  },
  "items": [
    {
      "description": "Mavi - SWEATSHIRT",
      "quantity": "1.0000",
      "unit": "piece",
      "unit_price": { "amount": "1.0000", "currency": "GEL" },
      "subtotal": null,
      "vat_amount": null,
      "total": { "amount": "1.0000", "currency": "GEL" },
      "vat_treatment": "unknown",
      "sku": null,
      "barcode": null,
      "item_code": "2141",
      "excise_amount": null,
      "excise_code": null,
      "sub_charges": []
    }
  ],
  "subtotal_total": { "amount": "1.0000", "currency": "GEL" },
  "vat_total": null,
  "discount_total": null,
  "shipping_cost": { "amount": "0", "currency": "GEL" },
  "grand_total": { "amount": "1.0000", "currency": "GEL" },
  "is_vat_invoice": false,
  "is_reverse_vat": false,
  "vat_treatment_overall": "unknown",
  "vat_treatment_reason": "Waybill header marks both parties as VAT payers but no VAT breakdown is shown; nominal 1 GEL price suggests test data",
  "is_free_of_charge": false,
  "references_other_document": null,
  "transport": {
    "start_address": "temqa 123",
    "end_address": "gldani 123",
    "driver": {
      "name": "ბექა ბექაური",
      "tin": "01701113857",
      "tin_label_present": true,
      "party_type": "individual_ge",
      "address": null,
      "bank_account": null,
      "script": "mkhedruli",
      "extracted_from_region": null
    },
    "vehicle_plate": "ti223tu",
    "has_trailer": false,
    "transport_cost": { "amount": "0", "currency": "GEL" },
    "transport_cost_payer": "seller",
    "begin_date": "2026-05-19T03:53:02",
    "delivery_date": null
  },
  "notes": null,
  "contains_pii_beyond_parties": false,
  "extraction_notes": [
    "Total in words: ერთი ლარი და ნული თეთრი",
    "Addresses 'temqa 123' and 'gldani 123' are Latin transliterations of Georgian (თემქა, გლდანი) — preserve as-typed by the user; do not auto-convert to Mkhedruli",
    "Item description 'Mavi - SWEATSHIRT' is a brand/product name in Latin — preserve as-typed",
    "Vehicle plate 'ti223tu' is lowercase Latin — preserve as-typed",
    "Buyer TIN has 11 digits; classified as individual_ge based on TIN length"
  ],
  "extraction": {
    "source_filename": "Waybill_List10.pdf",
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

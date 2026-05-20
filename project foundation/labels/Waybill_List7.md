# Gold label: Waybill_List7 (from `data/labeling_forms/label_Waybill_List7.md`)

```json
{
  "accepted": true,
  "rejection_reason": null,
  "document_type": "waybill",
  "document_number": "ელ-0979333993",
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
      "description": "ფიცარი",
      "quantity": "11.1100",
      "unit": "m3",
      "unit_price": { "amount": "20.0000", "currency": "GEL" },
      "subtotal": null,
      "vat_amount": null,
      "total": { "amount": "222.2000", "currency": "GEL" },
      "vat_treatment": "unknown",
      "sku": null,
      "barcode": null,
      "item_code": "ხეტყე-12",
      "excise_amount": null,
      "excise_code": null,
      "sub_charges": []
    }
  ],
  "subtotal_total": { "amount": "222.2000", "currency": "GEL" },
  "vat_total": null,
  "discount_total": null,
  "shipping_cost": null,
  "grand_total": { "amount": "222.2000", "currency": "GEL" },
  "is_vat_invoice": false,
  "is_reverse_vat": false,
  "vat_treatment_overall": "unknown",
  "vat_treatment_reason": "Waybill header marks both parties as VAT payers but no VAT breakdown is shown",
  "is_free_of_charge": false,
  "references_other_document": "იმპორტი / 2985 / 11.01.2023",
  "transport": {
    "start_address": "საქართველო თბილისი ისანი-სამგორი კალოუბნის ქ 25",
    "end_address": "საქართველო აჭარა ქობულეთის რაიონი ძნელაძის 54",
    "driver": null,
    "vehicle_plate": null,
    "has_trailer": false,
    "transport_cost": null,
    "transport_cost_payer": null,
    "begin_date": "2026-05-19T11:30:06",
    "delivery_date": null
  },
  "notes": null,
  "contains_pii_beyond_parties": false,
  "extraction_notes": [
    "TIMBER WAYBILL (ხე-ტყის სასაქონლო ზედნადები) — different document subtype from standard waybill",
    "Timber waybill columns differ from standard: ფირნიშის/ცნობის № (marker/certificate no.) replaces barcode column",
    "Transport mode field contains garbage value 'hjuhyugh' — clearly user error or test data; transport block driver and plate are empty/X",
    "Origin-document reference (იმპორტი / 2985 / 11.01.2023) is mandatory on timber waybills — captured in references_other_document",
    "Total in words: ორას ოცდაორი ლარი და ოცი თეთრი",
    "If schema is extended, document_subtype = 'timber' would apply here"
  ],
  "extraction": {
    "source_filename": "Waybill_List7.pdf",
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

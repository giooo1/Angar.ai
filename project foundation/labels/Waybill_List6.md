# Gold label: Waybill_List6 (from `data/labeling_forms/label_Waybill_List6.md`)

```json
{
  "accepted": true,
  "rejection_reason": null,
  "document_type": "waybill",
  "document_number": "ელ-0979336565",
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
      "description": "არმატურა 18მმ",
      "quantity": "5.0000",
      "unit": "ton",
      "unit_price": { "amount": "1500.0000", "currency": "GEL" },
      "subtotal": null,
      "vat_amount": null,
      "total": { "amount": "7500.0000", "currency": "GEL" },
      "vat_treatment": "unknown",
      "sku": null,
      "barcode": null,
      "item_code": "2234",
      "excise_amount": null,
      "excise_code": null,
      "sub_charges": []
    }
  ],
  "subtotal_total": { "amount": "7500.0000", "currency": "GEL" },
  "vat_total": null,
  "discount_total": null,
  "shipping_cost": { "amount": "100", "currency": "GEL" },
  "grand_total": { "amount": "7500.0000", "currency": "GEL" },
  "is_vat_invoice": false,
  "is_reverse_vat": false,
  "vat_treatment_overall": "unknown",
  "vat_treatment_reason": "Waybill header marks both parties as VAT payers but no VAT breakdown is shown on the document; prices may be VAT-inclusive per RS.ge convention",
  "is_free_of_charge": false,
  "references_other_document": null,
  "transport": {
    "start_address": "ქუთაისი",
    "end_address": "ქუთაისი",
    "driver": {
      "name": "ანდრია",
      "tin": "37501060940",
      "tin_label_present": true,
      "party_type": "individual_ge",
      "address": null,
      "bank_account": null,
      "script": "mkhedruli",
      "extracted_from_region": null
    },
    "vehicle_plate": "dd371zd",
    "has_trailer": false,
    "transport_cost": { "amount": "100", "currency": "GEL" },
    "transport_cost_payer": "seller",
    "begin_date": "2026-05-19T11:36:33",
    "delivery_date": null
  },
  "notes": null,
  "contains_pii_beyond_parties": false,
  "extraction_notes": [
    "Total in words: შვიდი ათას ხუთასი ლარი და ნული თეთრი",
    "Vehicle plate 'dd371zd' is lowercase Latin — preserve as-typed; does not match RS.ge AANNNAA uppercase convention",
    "Trailer field shows '0' (explicit zero) rather than 'X' — interpreted as no trailer",
    "Shipping cost of 100 GEL is paid by seller and is not included in line-item grand total"
  ],
  "extraction": {
    "source_filename": "Waybill_List6.pdf",
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

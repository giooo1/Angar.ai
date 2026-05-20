# Gold label: Waybill_List2 (from `data/labeling_forms/label_Waybill_List2.md`)

```json
{
  "accepted": true,
  "rejection_reason": null,
  "document_type": "waybill",
  "document_number": "ელ-0979414331",
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
    "name": "სატესტო კოდი1",
    "tin": "206322102",
    "tin_label_present": true,
    "party_type": "legal_entity",
    "address": null,
    "bank_account": null,
    "script": "mkhedruli",
    "extracted_from_region": null
  },
  "items": [
    {
      "description": "sab",
      "quantity": "1.0000",
      "unit": "piece",
      "unit_price": { "amount": "0.0000", "currency": "GEL" },
      "subtotal": null,
      "vat_amount": null,
      "total": { "amount": "0.0000", "currency": "GEL" },
      "vat_treatment": "unknown",
      "sku": null,
      "barcode": null,
      "item_code": "20100010",
      "excise_amount": null,
      "excise_code": null,
      "sub_charges": []
    }
  ],
  "subtotal_total": { "amount": "0.0000", "currency": "GEL" },
  "vat_total": null,
  "discount_total": null,
  "shipping_cost": { "amount": "0", "currency": "GEL" },
  "grand_total": { "amount": "0.0000", "currency": "GEL" },
  "is_vat_invoice": false,
  "is_reverse_vat": false,
  "vat_treatment_overall": "unknown",
  "vat_treatment_reason": "All amounts zero — placeholder / internal transfer between same TIN",
  "is_free_of_charge": true,
  "references_other_document": null,
  "transport": {
    "start_address": "თბილისი ბელიაშვილი (1002)",
    "end_address": "Tbilisi",
    "driver": {
      "name": "ხატია თვაური",
      "tin": "01013024835",
      "tin_label_present": true,
      "party_type": "individual_ge",
      "address": null,
      "bank_account": null,
      "script": "mkhedruli",
      "extracted_from_region": null
    },
    "vehicle_plate": "AA301",
    "has_trailer": false,
    "transport_cost": { "amount": "0", "currency": "GEL" },
    "transport_cost_payer": "buyer",
    "begin_date": "2026-05-19T15:19:04",
    "delivery_date": null
  },
  "notes": null,
  "contains_pii_beyond_parties": false,
  "extraction_notes": [
    "Operation type: შიდა გადაზიდვა (internal transport — seller and buyer are the same TIN)",
    "End address is in Latin script while start address is in Mkhedruli — user-entered mixed-script case",
    "Item description 'sab' is Latin transliteration of საბ; preserve as-typed (do not convert script)"
  ],
  "extraction": {
    "source_filename": "Waybill_List2.pdf",
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

# Gold label: Waybill_List5 (from `data/labeling_forms/label_Waybill_List5.md`)

```json
{
  "accepted": true,
  "rejection_reason": null,
  "document_type": "waybill",
  "document_number": "ელ-0979392922",
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
      "description": "250ლ კოკა-კოლა",
      "quantity": "60.0000",
      "unit": "piece",
      "unit_price": { "amount": "0.8100", "currency": "GEL" },
      "subtotal": null,
      "vat_amount": null,
      "total": { "amount": "48.6000", "currency": "GEL" },
      "vat_treatment": "unknown",
      "sku": null,
      "barcode": null,
      "item_code": "11",
      "excise_amount": null,
      "excise_code": null,
      "sub_charges": []
    },
    {
      "description": "0.330ლ კოკა-კოლა ქილა",
      "quantity": "24.0000",
      "unit": "piece",
      "unit_price": { "amount": "1.4900", "currency": "GEL" },
      "subtotal": null,
      "vat_amount": null,
      "total": { "amount": "35.7600", "currency": "GEL" },
      "vat_treatment": "unknown",
      "sku": null,
      "barcode": null,
      "item_code": "12",
      "excise_amount": null,
      "excise_code": null,
      "sub_charges": []
    },
    {
      "description": "0.500ლ კოკა-კოლა (12ც)",
      "quantity": "48.0000",
      "unit": "piece",
      "unit_price": { "amount": "1.4200", "currency": "GEL" },
      "subtotal": null,
      "vat_amount": null,
      "total": { "amount": "68.1600", "currency": "GEL" },
      "vat_treatment": "unknown",
      "sku": null,
      "barcode": null,
      "item_code": "13",
      "excise_amount": null,
      "excise_code": null,
      "sub_charges": []
    },
    {
      "description": "0.500ლ კოკა-კოლა შაქრის გარეშე (12ც)",
      "quantity": "24.0000",
      "unit": "piece",
      "unit_price": { "amount": "1.4200", "currency": "GEL" },
      "subtotal": null,
      "vat_amount": null,
      "total": { "amount": "34.0800", "currency": "GEL" },
      "vat_treatment": "unknown",
      "sku": null,
      "barcode": null,
      "item_code": "15",
      "excise_amount": null,
      "excise_code": null,
      "sub_charges": []
    }
  ],
  "subtotal_total": { "amount": "186.6000", "currency": "GEL" },
  "vat_total": null,
  "discount_total": null,
  "shipping_cost": { "amount": "0", "currency": "GEL" },
  "grand_total": { "amount": "186.6000", "currency": "GEL" },
  "is_vat_invoice": false,
  "is_reverse_vat": false,
  "vat_treatment_overall": "unknown",
  "vat_treatment_reason": "Waybill header marks both parties as VAT payers but no VAT breakdown is shown on the document; prices may be VAT-inclusive per RS.ge convention",
  "is_free_of_charge": false,
  "references_other_document": null,
  "transport": {
    "start_address": "ქ.თბილისი",
    "end_address": "შერიფ ხიმშიაშვილი 22",
    "driver": {
      "name": "ჯიმი ქიქავა",
      "tin": "61006075896",
      "tin_label_present": true,
      "party_type": "individual_ge",
      "address": null,
      "bank_account": null,
      "script": "mkhedruli",
      "extracted_from_region": null
    },
    "vehicle_plate": "PO111HS",
    "has_trailer": false,
    "transport_cost": { "amount": "0", "currency": "GEL" },
    "transport_cost_payer": "seller",
    "begin_date": "2026-05-19T14:27:49",
    "delivery_date": null
  },
  "notes": null,
  "contains_pii_beyond_parties": false,
  "extraction_notes": [
    "Total in words: ას ოთხმოცდაექვსი ლარი და სამოცი თეთრი",
    "Beverage line item descriptions begin with volume specs (250ლ, 0.330ლ, 0.500ლ) — preserve as written",
    "Item code numeric IDs (11–15) are seller-internal SKUs, not standard barcodes",
    "Same transport leg as Waybill_List4 (same driver, plate, route) — possibly batched delivery"
  ],
  "extraction": {
    "source_filename": "Waybill_List5.pdf",
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

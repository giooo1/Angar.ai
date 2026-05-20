# Gold label: Waybill_List3 (from `data/labeling_forms/label_Waybill_List3.md`)

```json
{
  "accepted": true,
  "rejection_reason": null,
  "document_type": "waybill",
  "document_number": "ელ-0979406347",
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
      "description": "ცული",
      "quantity": "500.0000",
      "unit": "piece",
      "unit_price": { "amount": "70.0000", "currency": "GEL" },
      "subtotal": null,
      "vat_amount": null,
      "total": { "amount": "35000.0000", "currency": "GEL" },
      "vat_treatment": "unknown",
      "sku": null,
      "barcode": null,
      "item_code": "9911",
      "excise_amount": null,
      "excise_code": null,
      "sub_charges": []
    },
    {
      "description": "ატვიორკა",
      "quantity": "1200.0000",
      "unit": "piece",
      "unit_price": { "amount": "3.0000", "currency": "GEL" },
      "subtotal": null,
      "vat_amount": null,
      "total": { "amount": "3600.0000", "currency": "GEL" },
      "vat_treatment": "unknown",
      "sku": null,
      "barcode": null,
      "item_code": "9922",
      "excise_amount": null,
      "excise_code": null,
      "sub_charges": []
    },
    {
      "description": "ბრტყელტუჩა",
      "quantity": "700.0000",
      "unit": "piece",
      "unit_price": { "amount": "14.0000", "currency": "GEL" },
      "subtotal": null,
      "vat_amount": null,
      "total": { "amount": "9800.0000", "currency": "GEL" },
      "vat_treatment": "unknown",
      "sku": null,
      "barcode": null,
      "item_code": "9933",
      "excise_amount": null,
      "excise_code": null,
      "sub_charges": []
    },
    {
      "description": "ბეტონის ლურსმანი 120სმ",
      "quantity": "350.0000",
      "unit": "piece",
      "unit_price": { "amount": "12.0000", "currency": "GEL" },
      "subtotal": null,
      "vat_amount": null,
      "total": { "amount": "4200.0000", "currency": "GEL" },
      "vat_treatment": "unknown",
      "sku": null,
      "barcode": null,
      "item_code": "9944",
      "excise_amount": null,
      "excise_code": null,
      "sub_charges": []
    }
  ],
  "subtotal_total": { "amount": "52600.0000", "currency": "GEL" },
  "vat_total": null,
  "discount_total": null,
  "shipping_cost": { "amount": "0", "currency": "GEL" },
  "grand_total": { "amount": "52600.0000", "currency": "GEL" },
  "is_vat_invoice": false,
  "is_reverse_vat": false,
  "vat_treatment_overall": "unknown",
  "vat_treatment_reason": "Waybill header marks both parties as VAT payers but no VAT breakdown is shown on the document; prices may be VAT-inclusive per RS.ge convention",
  "is_free_of_charge": false,
  "references_other_document": null,
  "transport": {
    "start_address": "გარადოკი 29",
    "end_address": "2",
    "driver": {
      "name": "ანა მაისურაძე",
      "tin": "01027087329",
      "tin_label_present": true,
      "party_type": "individual_ge",
      "address": null,
      "bank_account": null,
      "script": "mkhedruli",
      "extracted_from_region": null
    },
    "vehicle_plate": "LL557VV",
    "has_trailer": false,
    "transport_cost": { "amount": "0", "currency": "GEL" },
    "transport_cost_payer": "buyer",
    "begin_date": "2026-05-19T15:00:15",
    "delivery_date": "2026-05-19T15:01:00"
  },
  "notes": "კორექტირების თარიღი: 19/05/2026 15:01:31 (correction timestamp)",
  "contains_pii_beyond_parties": false,
  "extraction_notes": [
    "Document was corrected — correction timestamp appears at top of document (კორექტირების თარიღი)",
    "Total in words: ორმოცდათორმეტი ათას ექვსასი ლარი და ნული თეთრი",
    "Buyer TIN has 11 digits and buyer name pattern looks like test data; classified as individual_ge based on TIN length",
    "Buyer name 'სატესტოk სატესტოk' contains Latin 'k' suffix — mixed-script user input"
  ],
  "extraction": {
    "source_filename": "Waybill_List3.pdf",
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

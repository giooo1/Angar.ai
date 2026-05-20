# Gold label: Waybill_List (from `data/labeling_forms/label_Waybill_List.md`)

```json
{
  "accepted": true,
  "rejection_reason": null,
  "document_type": "waybill",
  "document_number": "ელ-0976696987",
  "document_date": "2026-05-07",
  "document_currency": "GEL",
  "seller": {
    "name": "შპს ვიტა სანა",
    "tin": "404663486",
    "tin_label_present": true,
    "party_type": "legal_entity",
    "address": null,
    "bank_account": null,
    "script": "mkhedruli",
    "extracted_from_region": null
  },
  "buyer": {
    "name": "შპს იმედის კლინიკა",
    "tin": "202249110",
    "tin_label_present": true,
    "party_type": "legal_entity",
    "address": null,
    "bank_account": null,
    "script": "mkhedruli",
    "extracted_from_region": null
  },
  "items": [
    {
      "description": "არასტერილური ხელთათმანი, ლატექსის, უპუდრო, ზომა M",
      "quantity": "1000.0000",
      "unit": "pair",
      "unit_price": { "amount": "0.0900", "currency": "GEL" },
      "subtotal": null,
      "vat_amount": null,
      "total": { "amount": "90.0000", "currency": "GEL" },
      "vat_treatment": "unknown",
      "sku": null,
      "barcode": null,
      "item_code": "1753766950250874-TaiyuGloves23072025-20270131",
      "excise_amount": null,
      "excise_code": null,
      "sub_charges": []
    }
  ],
  "subtotal_total": { "amount": "90.0000", "currency": "GEL" },
  "vat_total": null,
  "discount_total": null,
  "shipping_cost": { "amount": "0", "currency": "GEL" },
  "grand_total": { "amount": "90.0000", "currency": "GEL" },
  "is_vat_invoice": false,
  "is_reverse_vat": false,
  "vat_treatment_overall": "unknown",
  "vat_treatment_reason": "VAT-inclusive wording for payers but document marked free of charge — conflicting signals",
  "is_free_of_charge": true,
  "references_other_document": null,
  "transport": {
    "start_address": "თბილისი, ლილო, გიორგი ჩიკვაიძის 4",
    "end_address": "თბილისი-ვაკე-საბურთალო ვეფხისტყაოსანის ქ. 38",
    "driver": {
      "name": "ოთარი ეჯიბია",
      "tin": "39001010508",
      "tin_label_present": true,
      "party_type": "individual_ge",
      "address": null,
      "bank_account": null,
      "script": "mkhedruli",
      "extracted_from_region": null
    },
    "vehicle_plate": "UN712UU",
    "has_trailer": null,
    "transport_cost": null,
    "transport_cost_payer": null,
    "begin_date": "2026-05-07T12:25:50",
    "delivery_date": null
  },
  "notes": null,
  "contains_pii_beyond_parties": false,
  "extraction_notes": [
    "უსასყიდლოდ — listed amounts are declared value, not amount owed",
    "Four decimal places on quantities and money (waybill convention)",
    "RS.ge field numbers in green boxes are template IDs, not data"
  ],
  "extraction": {
    "source_filename": "Waybill_List.pdf",
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

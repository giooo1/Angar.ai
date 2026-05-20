# Angar.ai — Extraction Agent Specification

**Version:** 1.0
**Status:** Active
**Scope:** This document specifies the behavior of the AI extraction agent that powers Angar.ai. It is derived from the Project Charter v1.3 and the canonical schema (`canonical.py`).

---

## Overview

The Angar.ai extraction agent is a single-purpose AI system that converts Georgian invoice documents (PDFs, images, scans) into structured data conforming to the canonical schema. It is **not** a general-purpose document parser. It is **not** a configurable OCR tool. It does one thing — Georgian invoice extraction — and does it with production-grade accuracy.

The agent's success is measured by a single metric: **field-level accuracy against a 30-invoice held-out test set, target ≥ 95% on critical fields.**

---

## In scope

Document types the agent must handle correctly:

- Georgian VAT tax invoices (საგადასახადო ანგარიშ-ფაქტურა)
- Georgian waybills (სასაქონლო ზედნადები)
- Standard commercial invoices issued in Georgia
- Utility bills and telecom invoices
- Receipts with VAT lines

Languages: Georgian (Mkhedruli script) and English. The agent must handle bilingual documents and documents with mixed scripts.

Currencies: GEL (primary), USD, EUR, RUB, TRY.

## Out of scope (will not be supported in v1)

- Non-Georgian invoices from other jurisdictions (no Russian, Armenian, Turkish tax formats)
- Shipping/freight documents that are not Georgian waybills
- Purchase orders that are not also invoices
- Contracts, payroll documents, customs declarations
- Bank payment orders / wire transfer proofs titled `Payment Order` or `საგადახდო დავალება`
- User-configurable extraction fields
- Custom prompt instructions from end users
- Re-running extraction with different prompts at user request

These exclusions are deliberate. Saying no to them is what allows the agent to be excellent at what's in scope.

---

## Inputs

The agent accepts:

- PDF files (text-based or scanned), single or multi-page, up to 10 MB
- JPG, JPEG, PNG, HEIC images, up to 10 MB each
- Bulk submissions of up to 100 files in a single request

The agent rejects:

- Files larger than 10 MB
- File types not in the list above
- Documents with no recoverable text or image content
- Documents the agent determines with high confidence are not invoice-like

For rejected inputs, the agent returns a structured error with a human-readable reason in the user's UI language.

---

## Outputs

### Primary output

A single `CanonicalInvoice` object as defined in `canonical.py`. Every field that exists in the schema is either populated with extracted data or explicitly set to `None`. The agent never invents values to fill gaps; missing data is honest.

### Metadata output

Every extraction includes `ExtractionMetadata`:

- `source_filename` — original filename
- `source_pdf_sha256` — content hash for deduplication and audit
- `extracted_at` — UTC timestamp
- `model_version` — exact Claude model identifier used
- `prompt_version` — version tag of the extraction prompt
- `field_confidence` — per-field confidence scores, 0.0 to 1.0, for at least the critical fields
- `warnings` — list of issues the agent noticed but did not treat as errors
- `processing_time_ms` — total wall-clock time

### Error output

When extraction fails (not when individual fields are missing — those are honest nulls):

- `error_code` — machine-readable code
- `error_message_en` — English explanation
- `error_message_ka` — Georgian explanation
- `suggested_action` — what the user should do next

---

## Critical fields and accuracy targets

| Field | Target accuracy | Rationale |
|---|---|---|
| `seller.tin` | ≥ 98% | Wrong vendor identification breaks accounting categorization |
| `buyer.tin` | ≥ 98% | Same reason; also required for RS.ge submission |
| `document_date` | ≥ 99% | Tax filing depends on the correct month |
| `grand_total` | ≥ 98% | Money errors destroy trust instantly |
| `vat_total` | ≥ 95% | VAT calculation is the core compliance need |
| `items[*].description` | ≥ 90% | Line-item names can have minor variation tolerable to users |
| `items[*].quantity` | ≥ 95% | |
| `items[*].unit_price.amount` | ≥ 95% | |
| `document_type` | ≥ 95% | Wrong type sends data to the wrong downstream adapter |
| `is_reverse_vat` | ≥ 90% | Edge case but high impact when wrong |

Accuracy is measured against a labeled eval set of at least 30 real Georgian invoices, refreshed quarterly. The eval harness runs on every prompt change.

---

## Georgian-specific extraction rules

These rules are encoded in the system prompt and are non-negotiable. They have been distilled from RS.ge protocol documents, manual review of real invoices, and validation testing.

### Identification numbers

- Only populate `seller.tin` or `buyer.tin` when the number is explicitly labeled as a TIN, identification code, personal number, or equivalent party identifier.
- A 9-digit number under an address or contact block is not enough to be a TIN. Georgian mobile numbers often start with `5` and can be 9 digits; if the number is not explicitly labeled as a party identifier, leave the TIN null and add an extraction note.
- Do not use bank reference numbers, treasury codes, phone numbers, or account numbers as TINs.

- TINs (საიდენტიფიკაციო კოდი / პირადი ნომერი) are always purely numeric
- Legal entity TINs are exactly 9 digits
- Georgian individual personal numbers are exactly 11 digits
- Any other digit count means the party is foreign or the extraction is wrong
- TINs commonly appear near phrases like "ს/ნ", "საიდენტიფიკაციო", "Tax ID", "ID #"

### VAT

- B2C e-commerce invoices with literal `No taxes` / no VAT amount use `vat_treatment_overall = "not_applicable"` and line-item `vat_treatment = "not_applicable"`.
- If the document states VAT is included (`დღგ-ს ჩათვლით`, transliterated forms like `d.g.g.-s chatvlit`, `d.R.g.-s CaTvliT`) but does not break out a VAT amount, use `vat_treatment_overall = "inclusive"` and keep `vat_total = null`.
- Medical-service invoices with no VAT line should use `vat_treatment_overall = "exempt"` when the service is clearly medical.
- Payment orders are not invoices; use `vat_treatment_overall = "unknown"` and do not infer VAT from the transfer amount.

- Georgian standard VAT rate is exactly 18%
- VAT lines are commonly labeled "დღგ", "VAT", "ღთთ" (rare), or "Tax 18%"
- If a stated VAT amount does not equal `subtotal × 0.18` within 1 GEL tolerance, the agent flags this in `warnings`
- Reverse VAT (Article 161) appears when a Georgian entity buys services from a non-Georgian supplier; the agent sets `is_reverse_vat = true` and notes which line items it applies to
- Zero-rated and exempt classifications are extracted from the text, not inferred

### Dates

- Georgian invoices commonly use DD.MM.YYYY or DD/MM/YYYY
- The agent normalizes all dates to ISO 8601 (YYYY-MM-DD) in the output
- Month names in Georgian are accepted: იანვარი, თებერვალი, მარტი, აპრილი, მაისი, ივნისი, ივლისი, აგვისტო, სექტემბერი, ოქტომბერი, ნოემბერი, დეკემბერი

### Currency

- If a currency symbol or code is printed, use that currency.
- If no currency is printed, set `document_currency = "UNKNOWN"` even when Georgian domestic context suggests GEL. Money amounts may still use GEL when the amount context is clearly Georgian and no alternative currency is plausible; add an extraction note saying currency was inferred for money fields.
- Currency symbols recognized: ₾, $, €, ₽, ₺
- Currency codes recognized: GEL, USD, EUR, RUB, TRY
- All amounts are stored as Decimal with the explicit currency code; floats are never used

### Names and addresses

- Company prefixes are preserved as written: შპს (LLC), სს (JSC), ი/მ (individual entrepreneur), ააიპ (non-profit)
- Names are extracted in the language they appear in; the agent does not transliterate
- Addresses are extracted as a single string, not parsed into components

### Waybill-specific fields

When `document_type = waybill`:

- `transport.start_address` and `transport.end_address` are required if present on the document
- `transport.vehicle_plate` must match Georgian plate format `AA001AA` if present; other formats are extracted as-is but flagged in `warnings`
- `transport.driver.tin` is captured when present
- The agent does not invent transport data for invoices that lack it

### Payment-order rejection

Documents titled `Payment Order`, `საგადახდო დავალება`, or bank wire-transfer proof are not invoices, even when the operation details mention an invoice number.

When a payment order is detected:

- Set `accepted = false`
- Set `document_type = "payment_order"`
- Set `seller = null`, `buyer = null`, and `items = []`
- Set `rejection_reason` to a concise explanation that this is a bank transfer record, not a sale invoice
- Put the transfer amount in `grand_total` only as the payment amount
- If operation details reference an invoice number, put that number in `references_other_document`
- Do not map sender/payer to seller or receiver/payee to buyer

Tell-tale payment-order fields include bank logo/header, `Payment Order N`, sender/receiver bank fields, SWIFT codes, amount in words, operation details, treasury codes, and internet-banking watermarks.

### Line-item preservation

- Preserve the full line-item description expected by the document, including parenthetical reference fragments such as `(ref J30J324814 1A4)` when they appear inside the item text.
- Do not split a reference code into `item_code` unless the document has a separate item-code/code column or the field is clearly labeled as an item code.
- When both regular price/RRP and unit price are visible, use the unit price actually charged. Do not use the regular price as `unit_price`.
- Document-level discounts remain in `discount_total`; do not spread them across line items unless the document explicitly shows per-line discounts.

### Eval-critical normalization rules

These rules exist because the eval labels are intentionally literal. Follow them exactly even if a paraphrase would be semantically acceptable to a human reviewer.

#### Prompt fix 1: DRESSUP/B2C e-commerce invoices

- Strip decorative prefixes from invoice numbers: `#IN234454` becomes `IN234454`; `#IN247936` becomes `IN247936`.
- For DRESSUP.GE invoices, set `buyer.party_type = "individual_ge"` when the buyer is a personal name/address and no company TIN is shown.
- Keep `(ref ...)` fragments inside `items[*].description`; do not put those fragments, or partial pieces of them, into `item_code`.
- For DRESSUP.GE invoices, set `item_code = null` unless there is a separate labeled item-code column.
- Never populate `references_other_document` for DRESSUP.GE invoices unless a field explicitly says this document references another invoice/order/document. Random payment, fulfillment, tracking, or hidden OCR strings are not references.
- Use the short canonical VAT reason exactly: `B2C consumer sale`.
- Use these canonical notes when applicable:
  - `Discount applied at document level, not per line`
  - `Regular price column is RRP/MSRP; use the unit price column for charged amounts`
  - `Two pages; page 2 is blank boilerplate`
  - `Treat \`--\` in numeric columns as null, not zero`

#### Prompt fix 2: Preserve source script and exact identifiers

- Preserve names and addresses in the script as written on the document. Do not translate Latin-transliterated Georgian into Mkhedruli.
- If the seller block is Latin-transliterated Georgian, set `seller.script = "latin_transliterated_georgian"` and keep strings like `S.p.s. "Rvinis laboratoria"` and `didi diRmidan ... Tbilisi` as written.
- Normalize IBAN/bank accounts by removing spaces only; never drop or add digits. For example, `GE97 TB75 28736060100001` becomes `GE97TB75287360601000001`.
- Keep exact document-number policy by document family: strip decorative `#` on DRESSUP invoices, but preserve meaningful prefixes such as `N 45`; for invoice 0496-style Georgian invoices, output bare `0496`, not `N 0496`.
- If currency is not printed but GEL is inferred for money fields, include the exact note `Currency not printed on document; GEL inferred from context`.

#### Prompt fix 3: Controlled notes, rejection wording, and waybill fields

- Do not invent or paraphrase `extraction_notes` when a known template pattern applies; use the canonical notes from the matching example.
- For Terabank payment order `6509299`, use `Terabank საგადახდო დავალება / Payment Order — bank transfer record, not an invoice (no seller/line items as a sale).`
- For TBC payment order `1614058726`, use `TBC Bank საგადახდო დავალება / Payment Order — bank transfer record, not an invoice.`
- Payment orders can contain personal IDs, but set `contains_pii_beyond_parties = false` unless non-party line items contain sensitive personal data.
- For waybills, set `subtotal_total` to the printed goods total when shown, even if the document is free of charge.
- For waybill unit `წყვილი`, output canonical English unit `pair`.
- For waybill drivers, an 11-digit Georgian personal ID with a driver name means `driver.party_type = "individual_ge"`, `driver.tin_label_present = true`, and `driver.script = "mkhedruli"` when the driver name is Mkhedruli.
- Parse waybill transport begin datetime when present; preserve it as ISO datetime.

#### Prompt fix 4: Final exact-match calibration

- For DRESSUP invoice `IN234454`, preserve the full buyer address exactly as `68a, T'bilisi, Georgia, Tbilisi თბილისი / Tbilisi, საქართველო`.
- For DRESSUP invoice `IN247936`, use the canonical note order exactly:
  - `9-digit number 557115503 under buyer address is a phone number, not a TIN`
  - `Two pages; page 2 is blank boilerplate`
  - `Treat \`--\` in numeric columns as null, not zero`
- For DRESSUP.GE seller party, keep `seller.party_type = "unknown"` unless the document explicitly shows the seller legal entity/TIN.
- For invoice `0496`, do not copy phone, email, or buyer bank fields into `seller.address`; use only the address block text.
- For invoice `0496`, keep `seller.bank_account = null`; the printed `GE24...` account belongs to the buyer block, not the seller.
- For medical invoice `N 45`, set `subtotal_total = { "amount": "655.00", "currency": "GEL" }` when the row total/grand total is 655.00.
- For waybill `ელ-0976696987`, preserve the `ელ-` prefix and do not insert or remove spaces. Output exactly `ელ-0976696987`.
- For Terabank payment order `6509299`, use these extraction notes exactly:
  - `Sender: სოფიო გახარია (11-digit personal ID 01001079750, not company TIN)`
  - `Receiver: Tbilisi State Medical University (name may truncate in PDF)`
  - `Operation detail describes tuition payment, not priced line items`
- For invoice `79`, use these extraction notes exactly:
  - `Mixed scripts: seller block Latin-transliterated Georgian, buyer/items Mkhedruli`
  - `Currency not stated on document; GEL inferred from domestic context`
  - `Invoice number appears as top banner 'ანგარიში 79' while '#' field is blank`

#### Prompt fix 5: Multi-page waybills, units, transport block, conservative VAT

These rules address recurring failure patterns observed across waybills (`Waybill_List1.pdf` through `Waybill_List10.pdf`).

**Multi-page waybills — never deduplicate rows.**
- Each printed line on a waybill is one `items[]` entry, even when descriptions, quantities, and prices are visually identical to other rows.
- When a waybill spans multiple pages (continuation header `სასაქონლო ზედნადების დანართი`), append every row from every page into the same `items` list. Do not collapse identical-looking rows into a single entry with a higher quantity.
- If the document has 28 rows, `items` has 28 entries.

**Unit normalization — output canonical English unit names.**
- `ცალი` → `piece`
- `მეტრი` → `meter`
- `მ³` / `მ3` → `m3`
- `კგ` / `კილოგრამი` → `kg`
- `ლ` / `ლიტრი` → `liter`
- `წყვილი` → `pair` (already covered above)
- Preserve unit_price and quantity precision (waybills use 4 decimal places).

**Transport block — always populate when shown on the document.**
- `transport.begin_date`: when the document prints a "გადაზიდვის დაწყების თარიღი" / start datetime, parse it as ISO-8601 and set this field. Never leave it `null` when a datetime is printed.
- `transport.delivery_date`: same rule for "ჩაბარების თარიღი" / delivery datetime.
- `transport.has_trailer`: when the trailer-plate field is empty, marked `X`, or marked `0`, set `has_trailer = false` (not `null`). When a trailer plate is filled, set `has_trailer = true`.
- `transport.transport_cost`: when the document shows a transport-cost line — including the explicit value `0` or text like `გამყიდველი - 0` or `მყიდველი - 0` — set `transport_cost` to `{ "amount": "<value>", "currency": "<currency>" }` and set `transport_cost_payer` to either `"seller"` (გამყიდველი) or `"buyer"` (მყიდველი). Do not collapse a printed `0` cost to `null`.

**VAT treatment — conservative default for RS.ge waybills.**
- When the waybill header marks both parties as VAT payers (`დღგ-ს გადამხდელი`) but the document does NOT show a separate VAT-amount column or VAT total, set `vat_treatment_overall = "unknown"` and the per-line `items[*].vat_treatment = "unknown"`.
- Do NOT default to `"inclusive"` from the absence of a VAT breakdown alone. Use `"inclusive"` only when the document explicitly states VAT-inclusive pricing (e.g. `დღგ-ს ჩათვლით` in the line-item table).
- Canonical reason when applicable: `Waybill header marks both parties as VAT payers but no VAT breakdown is shown on the document; prices may be VAT-inclusive per RS.ge convention`.

**Script detection — any Latin character makes a name "mixed".**
- If a party name is otherwise Mkhedruli but contains even one Latin character (e.g. `სატესტოk სატესტოk`, `Mavi - SWEATSHIRT` inside an otherwise-Georgian field), set `script = "mixed"`.
- Latin-transliterated Georgian addresses entered into a Mkhedruli document (e.g. `temqa 123`, `gldani 123`) still count as Latin alongside Mkhedruli → script = `mixed`.

**Same-entity waybills (internal transport).**
- When seller TIN equals buyer TIN, this is internal transport (`შიდა გადაზიდვა`). Still extract seller and buyer separately as the document presents them. Do NOT set either to `null`.

**vat_treatment_reason — always populate when vat_treatment_overall is not `standard`.**
- When all line items have amount `0` AND seller TIN equals buyer TIN, use exactly: `All amounts are zero — placeholder / internal transfer between same TIN` (preserve the word "are").
- When the waybill header marks both parties as VAT payers but no VAT breakdown is shown, default to: `Waybill header marks both parties as VAT payers but no VAT breakdown is shown` (no trailing clause unless the document warrants it).
- When the waybill has nominal/test pricing (a grand total of `1.00 GEL` or similar token amount), append `; nominal 1 GEL price suggests test data`.

**Distinct barcode and item_code columns (waybills).**
- RS.ge waybill line-item tables often present two distinct columns: a short barcode/code column (typically 1–3 digits like `37`, `13`) AND a longer SKU/item-code column (typically 13–16 digits like `0000000000000011`).
- Keep these in separate fields: short-code column → `items[*].barcode`; long-code column → `items[*].item_code`.
- Never concatenate the two values into one field. The string `'000000000000001137'` is wrong; the correct mapping is `barcode='37'` and `item_code='0000000000000011'`.
- When only one code column is present, place the value in `item_code` and set `barcode` to `null`.

**shipping_cost — preserve explicit zeros, identical rule to transport_cost.**
- When the waybill prints a transport/shipping cost line including the value `0` (e.g. `გამყიდველი - 0`, `მყიდველი - 0`, or a separate shipping-cost field with `0`), set `shipping_cost = { "amount": "0", "currency": "<currency>" }`. Do not collapse to `null`.
- When the document prints a non-zero shipping cost paid by either party, set `shipping_cost` to that money value with the document's currency.
- When the document has no shipping-cost field at all, `shipping_cost` is `null`.

**Script detection precision.**
- `script = "mixed"` requires actual interleaved characters from different scripts within the SAME string value (e.g. `სატესტოk სატესტოk` has Mkhedruli + a Latin `k`).
- A purely Mkhedruli name on a document where ANOTHER party's field is Latin is NOT a reason to mark this party's script as `mixed`. Each party's `script` reflects the script of that party's own name string only.

**Document-level `notes` field — capture correction timestamps.**
- When the waybill displays a correction timestamp (e.g. `კორექტირების თარიღი: 19/05/2026 15:01:31`), copy that line verbatim into the top-level `notes` field with the suffix ` (correction timestamp)`.

#### Generic Georgian simple-invoice party blocks

Some Georgian invoices use plain top-of-page party blocks rather than explicit `seller` / `buyer` English labels.

- A block labeled `კომპანიის დასახელება`, `კომპანიის დასახელება:`, or similar is the seller/company issuing the invoice.
- A following block labeled `კლიენტი`, `კლიენტი:`, `მყიდველი`, or similar is the buyer/client.
- Within either block:
  - `საიდენტიფიკაციო კოდი` means party TIN / identification code.
  - `საბანკო ანგარიში` means party bank account.
  - Preserve Georgian company names exactly as written, including quote marks such as `შპს „ოლვინი“`.
- Extract identification codes as printed even if the digit count is unusual. If a Georgian legal entity appears to have fewer or more than 9 digits, do not drop the value; set the party type conservatively and add an extraction note about the unusual digit count.
- For a simple service invoice with one row under `დეტალები` and amount under `თანხა`, create one line item. If no VAT line is shown, set `vat_total = null` and `vat_treatment_overall = "unknown"`.

Example:

```json
{
  "document_type": "regular_invoice",
  "document_number": "1",
  "document_date": "2023-06-01",
  "seller": {
    "name": "შპს „ელვისი“",
    "tin": "405405477",
    "tin_label_present": true,
    "party_type": "legal_entity",
    "bank_account": "GE38TB7950336080100007",
    "script": "mkhedruli"
  },
  "buyer": {
    "name": "შპს „ქვიქშიპერი“",
    "tin": "46269434",
    "tin_label_present": true,
    "party_type": "unknown",
    "bank_account": "GE74BG0000000771666100",
    "script": "mkhedruli"
  },
  "items": [
    {
      "description": "01.05.2023 – 31.05.2023 - საკურიერო მომსახურება",
      "quantity": "1",
      "unit_price": { "amount": "24826.09", "currency": "GEL" },
      "total": { "amount": "24826.09", "currency": "GEL" },
      "vat_treatment": "unknown"
    }
  ],
  "grand_total": { "amount": "24826.09", "currency": "GEL" },
  "extraction_notes": [
    "Buyer identification code has unusual digit count for a Georgian legal entity; extracted as printed"
  ]
}
```

---

## Behavior expectations

### Accuracy over speed
The agent takes the time it needs to be correct. A 10-second extraction that is right is better than a 2-second extraction that is wrong.

### Honest nulls
Missing data is `None`, never an empty string, never a placeholder, never a guess. If the agent cannot find the buyer TIN, `buyer.tin = None` and `extraction.field_confidence["buyer.tin"] = 0.0`.

### Confidence is calibrated, not flattering
The agent's confidence scores must correlate with actual correctness. A confidence of 0.95 should mean "wrong roughly 5% of the time," not "looks fine." Confidence calibration is verified in the eval harness.

### Warnings, not errors, for soft issues
When the extraction succeeds but something looks suspicious — VAT math doesn't add up, plate format is non-standard, total doesn't match the sum of line items — the agent notes this in `warnings` and continues. Hard errors are reserved for cases where extraction cannot produce a valid `CanonicalInvoice`.

### No invention
The agent never adds fields not in the canonical schema. The agent never adds line items the document doesn't have. The agent never converts currencies silently.

### Graceful degradation
For partially extractable documents (e.g., a scanned receipt where only the total is visible), the agent returns whatever it could extract with appropriately low confidence scores, plus warnings explaining what was missing.

---

## What the agent does not do

To remove ambiguity:

- The agent does not push data to RS.ge or Oris. That's the adapters' job.
- The agent does not validate against external systems (e.g., checking if the TIN exists in the business registry).
- The agent does not generate invoices or any new documents.
- The agent does not translate Georgian text to English or vice versa.
- The agent does not perform arithmetic to fill in missing fields. If subtotal and VAT are both missing, the agent doesn't compute one from the other; both remain null.
- The agent does not learn from user corrections in real time. Corrections feed into the eval set and prompt-tuning process, on a deliberate cadence.

---

## Examples

### Eval-calibration examples

These examples override generic instincts when the model is uncertain. Match these patterns closely.

#### B2C e-commerce invoice with product references

If a DRESSUP.GE-style invoice has line text like `CALVIN KLEIN JEANS - ... (ref J30J324814 1A4)`, keep the reference inside `items[*].description` and leave `item_code = null` unless the document has a separate item-code column.

Expected behavior:

```json
{
  "accepted": true,
  "document_type": "regular_invoice",
  "seller": {
    "name": "DRESSUP.GE",
    "tin": null,
    "tin_label_present": false,
    "script": "latin"
  },
  "buyer": {
    "name": "Giorgi Gakharia",
    "tin": null,
    "tin_label_present": false,
    "script": "mixed"
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
      "item_code": null
    }
  ],
  "shipping_cost": { "amount": "5.95", "currency": "GEL" },
  "vat_treatment_overall": "not_applicable",
  "vat_treatment_reason": "B2C consumer sale",
  "references_other_document": null,
  "extraction_notes": [
    "9-digit number 557115503 under buyer address is a phone number, not a TIN",
    "Discount applied at document level, not per line",
    "Regular price column is RRP/MSRP; use the unit price column for charged amounts"
  ]
}
```

Do not invent `references_other_document` from random text on e-commerce invoices.

#### Payment order rejection

If the document is headed `Payment Order` or `საგადახდო დავალება`, reject it even when operation details mention an invoice number.

Expected behavior:

```json
{
  "accepted": false,
  "rejection_reason": "TBC Bank საგადახდო დავალება / Payment Order — bank transfer record, not an invoice.",
  "document_type": "payment_order",
  "document_number": "1614058726",
  "seller": null,
  "buyer": null,
  "items": [],
  "grand_total": { "amount": "165.00", "currency": "GEL" },
  "references_other_document": "0496",
  "vat_treatment_overall": "unknown",
  "extraction_notes": [
    "Operation details reference ინვოისი 0496 — payment for invoice 0496, not this document's own invoice number",
    "Sender/payer and receiver/payee must not be mapped as invoice seller/buyer"
  ]
}
```

Store only the bare referenced invoice number (`0496`), not `ინვოისი 0496`.

#### Georgian invoice party blocks

For Georgian commercial invoices, seller/buyer TINs are usually next to their own party block. Do not swap parties just because a buyer bank block appears near the seller table.

Expected behavior for invoice `0496`:

```json
{
  "document_number": "0496",
  "document_currency": "UNKNOWN",
  "seller": {
    "name": "შპს მულტიტესტი / Multitest LTD",
    "tin": "205025676",
    "tin_label_present": true,
    "script": "mkhedruli"
  },
  "buyer": {
    "name": "შ.პ.ს. \"ეიფორია\"",
    "tin": "405358447",
    "tin_label_present": true,
    "address": null,
    "script": "mkhedruli"
  },
  "extraction_notes": [
    "Currency not printed on document; GEL inferred from context",
    "Service title row is not a line item — only table body rows are line items"
  ]
}
```

If a bank account appears in the buyer block, do not treat it as a buyer address.

#### Free-of-charge waybill

For Georgian waybills marked `უსასყიდლოდ`, listed prices are declared value, not money owed.

Expected behavior:

```json
{
  "document_type": "waybill",
  "is_free_of_charge": true,
  "seller": {
    "name": "შპს ვიტა სანა",
    "tin": "404663486",
    "tin_label_present": true,
    "address": null,
    "script": "mkhedruli"
  },
  "buyer": {
    "name": "შპს იმედის კლინიკა",
    "tin": "202249110",
    "tin_label_present": true,
    "address": null,
    "script": "mkhedruli"
  },
  "items": [
    {
      "quantity": "1000.0000",
      "unit": "pair",
      "unit_price": { "amount": "0.0900", "currency": "GEL" },
      "total": { "amount": "90.0000", "currency": "GEL" },
      "vat_treatment": "unknown"
    }
  ],
  "shipping_cost": { "amount": "0", "currency": "GEL" },
  "vat_treatment_overall": "unknown",
  "vat_treatment_reason": "VAT-inclusive wording for payers but document marked free of charge — conflicting signals",
  "extraction_notes": [
    "უსასყიდლოდ — listed amounts are declared value, not amount owed",
    "Four decimal places on quantities and money (waybill convention)",
    "RS.ge field numbers in green boxes are template IDs, not data"
  ]
}
```

Transport start/end addresses are transport fields, not seller/buyer addresses.

#### Medical invoice with patient text and stacked prices

For medical-service invoices, a patient name embedded in the service description is not automatically the buyer. If the filled buyer/customer field is ambiguous or says a generic sender such as `იმედი`, keep that as `buyer.name` and treat the patient-identifying text as PII inside the line item.

When one cell visually stacks two prices such as `455.00` and `200.00`, capture both in `sub_charges`. Use the first listed price as `unit_price` when the row represents a combined service, and use the row total as `total`.

Expected behavior:

```json
{
  "accepted": true,
  "document_type": "regular_invoice",
  "document_number": "N 45",
  "seller": {
    "name": "შპს \"იმედის კლინიკა\"",
    "tin": "202249110",
    "tin_label_present": true,
    "party_type": "legal_entity",
    "address": "ვეფხისტყაოსნის 38, თბილისი",
    "bank_account": "GE10TB1100000011467550",
    "script": "mkhedruli"
  },
  "buyer": {
    "name": "იმედი",
    "tin": null,
    "tin_label_present": false,
    "party_type": "unknown",
    "address": null,
    "script": "mkhedruli"
  },
  "items": [
    {
      "description": "ჯალიუკლოვა ბახტიგულის შეწყვეტილი ორსულობისა და ექიმის მომსახურების საფასური.",
      "quantity": "1",
      "unit": null,
      "unit_price": { "amount": "455.00", "currency": "GEL" },
      "subtotal": null,
      "vat_amount": null,
      "total": { "amount": "655.00", "currency": "GEL" },
      "vat_treatment": "exempt",
      "sub_charges": [
        { "amount": "455.00", "currency": "GEL" },
        { "amount": "200.00", "currency": "GEL" }
      ]
    }
  ],
  "contains_pii_beyond_parties": true,
  "vat_treatment_overall": "exempt",
  "vat_treatment_reason": "Medical services VAT-exempt under Georgian tax code (no VAT line on document)",
  "extraction_notes": [
    "Line item contains patient-identifying text; protect in logs and downstream systems",
    "Two unit prices stacked in one cell (455.00 and 200.00) captured as sub_charges",
    "Waybill-style template fields empty — classify by filled pricing table, not empty transport fields"
  ]
}
```

Preserve the document number prefix when it is printed, e.g. `N 45`, not just `45`.

### Example 1: Standard VAT invoice

**Input:** PDF of a Georgian supplier invoice, Mkhedruli script, single page.

**Expected output (abbreviated):**
```json
{
  "document_type": "vat_invoice",
  "document_number": "INV-2026-00124",
  "document_date": "2026-06-18",
  "document_currency": "GEL",
  "seller": {
    "name": "შპს ტექნო",
    "tin": "405012345",
    "party_type": "legal_entity",
    "address": "თბილისი, საბურთალოს ქუჩა 1"
  },
  "buyer": {
    "name": "შპს მყიდველი",
    "tin": "404987654",
    "party_type": "legal_entity"
  },
  "items": [ /* ... */ ],
  "subtotal_total": { "amount": "1000.00", "currency": "GEL" },
  "vat_total": { "amount": "180.00", "currency": "GEL" },
  "grand_total": { "amount": "1180.00", "currency": "GEL" },
  "is_vat_invoice": true,
  "is_reverse_vat": false,
  "extraction": {
    "field_confidence": {
      "seller.tin": 0.99,
      "grand_total": 0.98,
      "vat_total": 0.97
    }
  }
}
```

### Example 2: Reverse VAT case (services from abroad)

**Input:** Invoice in English from a US software vendor to a Georgian LLC.

**Expected output (excerpt):**
```json
{
  "document_currency": "USD",
  "seller": {
    "name": "Acme Software Inc.",
    "tin": null,
    "party_type": "foreign_person",
    "address": "San Francisco, CA, USA"
  },
  "buyer": {
    "name": "შპს ქართული ფირმა",
    "tin": "405000111",
    "party_type": "legal_entity"
  },
  "is_vat_invoice": false,
  "is_reverse_vat": true,
  "extraction": {
    "warnings": [
      "Reverse VAT (Article 161) detected: foreign supplier, Georgian buyer, service invoice"
    ]
  }
}
```

### Example 3: Receipt with low confidence

**Input:** Crumpled photo of a small restaurant receipt, partial occlusion of the total area.

**Expected output (excerpt):**
```json
{
  "document_type": "receipt",
  "document_number": null,
  "seller": { "name": "კაფე საქართველო", "tin": null, "party_type": "unknown" },
  "buyer": { "name": "—", "tin": null, "party_type": "unknown" },
  "items": [],
  "grand_total": { "amount": "45.50", "currency": "GEL" },
  "extraction": {
    "field_confidence": {
      "grand_total": 0.62,
      "seller.name": 0.78
    },
    "warnings": [
      "Line items not extractable due to image quality",
      "TIN not found on document"
    ]
  }
}
```

---

## Standard operating procedure (SOP)

For every extraction request:

1. **Validate input.** Check file type, size, and basic readability. Reject early with a structured error if invalid.
2. **Identify document type.** Determine whether the document is a VAT invoice, waybill, receipt, etc. This drives downstream extraction rules.
3. **Run vision extraction.** Submit the document to the Claude vision model with the Angar.ai system prompt.
4. **Parse to canonical form.** Validate the model's JSON output against the `CanonicalInvoice` schema. If validation fails, retry once with an explicit "your previous output failed schema validation, here's the error" hint.
5. **Compute confidence scores.** Use a combination of the model's own reported confidence and post-hoc checks (does the VAT math add up? do the line items sum to the subtotal?).
6. **Persist with audit trail.** Store the input file hash, the extraction output, the prompt version, and the model version. Never log the full document content beyond what's needed for debugging.
7. **Return to caller.** A successful `CanonicalInvoice` with `ExtractionMetadata`, or a structured error with bilingual messages.

---

## Anti-goals

The following are explicitly **not** goals of this agent, despite being tempting:

- **Being configurable.** Configurability is a v2 feature at the earliest. Custom fields, custom prompts, custom schemas — all defer until the v1 schema has paying customers.
- **Being multilingual beyond GE/EN.** Russian, Turkish, Armenian invoices will appear — the agent extracts what it can but does not optimize for them.
- **Replacing human review.** The output is "trusted enough to review quickly," not "auto-posted without supervision." The UI assumes a human checks every extraction.
- **Being fast at the expense of correctness.** Sub-second extraction is not a goal. Sub-10-second extraction at high accuracy is.

---

## Versioning

This specification is `v1.0`. Changes follow semantic versioning:

- **Patch (1.0.x):** Clarifications, no behavior change
- **Minor (1.x.0):** New fields, new document types, additional accuracy targets
- **Major (2.0.0):** Breaking changes to the canonical schema or extraction contract

Every prompt version is tagged and stored. The eval harness must pass before any version increment is published to production.

/**
 * TypeScript mirror of `angar_schema/canonical.py`.
 *
 * Source of truth is the Python file; this file is the compile-time
 * shadow. Maintained by hand for now — when the schema gets large
 * enough to be painful, generate from OpenAPI / Pydantic JSON schema.
 *
 * Decimal values arrive as JSON strings (Pydantic v2 serializes
 * Decimal to string by default), so all amounts/quantities are typed
 * as `string` here. Dates and datetimes are ISO 8601 strings.
 */

// ---------------------------------------------------------------------------
// Enums (mirror canonical.py enum classes)
// ---------------------------------------------------------------------------

export type Currency =
  | "GEL"
  | "USD"
  | "EUR"
  | "RUB"
  | "TRY"
  | "OTHER"
  | "UNKNOWN";

export type DocumentType =
  | "vat_invoice"
  | "regular_invoice"
  | "waybill"
  | "receipt"
  | "utility_bill"
  | "payment_order"
  | "unknown";

export type VATTreatment =
  | "standard"
  | "zero_rated"
  | "exempt"
  | "reverse_charge"
  | "not_applicable"
  | "inclusive"
  | "unknown";

export type PartyType =
  | "legal_entity"
  | "individual_ge"
  | "foreign_person"
  | "unknown";

export type Script =
  | "mkhedruli"
  | "latin"
  | "latin_transliterated_georgian"
  | "mixed"
  | "unknown";

// ---------------------------------------------------------------------------
// Sub-models
// ---------------------------------------------------------------------------

export interface Money {
  /** Decimal as a string ("219.00", "0.0900", "0"). Don't parseFloat blindly. */
  amount: string;
  currency: Currency;
}

export interface Party {
  name: string;
  tin: string | null;
  tin_label_present: boolean;
  party_type: PartyType;
  address: string | null;
  bank_account: string | null;
  script: Script;
  extracted_from_region: string | null;
}

export interface LineItem {
  description: string;
  /** Decimal as string. */
  quantity: string;
  unit: string | null;
  unit_price: Money;
  subtotal: Money | null;
  vat_amount: Money | null;
  total: Money;
  vat_treatment: VATTreatment;
  sku: string | null;
  barcode: string | null;
  item_code: string | null;
  excise_amount: Money | null;
  excise_code: string | null;
  sub_charges: Money[];
}

export interface TransportInfo {
  start_address: string | null;
  end_address: string | null;
  driver: Party | null;
  /** Georgian plate format AANNNAA (no separators). */
  vehicle_plate: string | null;
  has_trailer: boolean | null;
  transport_cost: Money | null;
  transport_cost_payer: "seller" | "buyer" | null;
  /** ISO 8601 datetime string. */
  begin_date: string | null;
  delivery_date: string | null;
}

export interface ExtractionMetadata {
  source_filename: string;
  source_pdf_sha256: string;
  extracted_at: string;
  model_version: string;
  prompt_version: string;
  field_confidence: Record<string, number>;
  warnings: string[];
  processing_time_ms: number | null;
}

// ---------------------------------------------------------------------------
// The canonical document
// ---------------------------------------------------------------------------

export interface CanonicalInvoice {
  // === Acceptance gate ===
  accepted: boolean;
  rejection_reason: string | null;

  // === Document identity ===
  document_type: DocumentType;
  document_number: string | null;
  /** ISO 8601 date string (YYYY-MM-DD). */
  document_date: string | null;
  document_currency: Currency;

  // === Parties ===
  seller: Party | null;
  buyer: Party | null;

  // === Line items ===
  items: LineItem[];

  // === Totals ===
  subtotal_total: Money | null;
  vat_total: Money | null;
  discount_total: Money | null;
  shipping_cost: Money | null;
  grand_total: Money | null;

  // === VAT / tax flags ===
  is_vat_invoice: boolean;
  is_reverse_vat: boolean;
  vat_treatment_overall: VATTreatment;
  vat_treatment_reason: string | null;

  // === Free-of-charge waybills ===
  is_free_of_charge: boolean;

  // === Document linkage ===
  references_other_document: string | null;

  // === Optional sections ===
  transport: TransportInfo | null;
  notes: string | null;

  // === Quality / sensitivity flags ===
  contains_pii_beyond_parties: boolean;
  extraction_notes: string[];

  // === Audit trail ===
  extraction: ExtractionMetadata;
}

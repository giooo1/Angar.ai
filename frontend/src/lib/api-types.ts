/**
 * TypeScript mirrors of backend/api_schemas.py.
 * When the backend changes shape, change this file too. The backend's
 * OpenAPI spec at http://localhost:8000/openapi.json is the source of
 * truth at runtime; this file is the compile-time shadow.
 */

import type { CanonicalInvoice } from "./canonical";

export type ExtractionStatus =
  | "pending"
  | "running"
  | "completed"
  | "failed";

export interface UploadResponse {
  document_id: string;
  extraction_id: string;
  status: ExtractionStatus;
}

export interface ExtractionStatusResponse {
  document_id: string;
  extraction_id: string;
  status: ExtractionStatus;
  prompt_version: string;
  model_version: string;
  canonical_data: CanonicalInvoice | null;
  warnings: string[];
  error_code: string | null;
  error_message: string | null;
  /** Per-field heuristic confidence in [0, 1]. Keys mirror dotted paths
   *  like `seller.tin`, `grand_total.amount`. Empty `{}` for extractions
   *  predating the WS2 confidence heuristic. */
  field_confidence: Record<string, number>;
  processing_time_ms: number | null;
  /** ISO 8601 UTC timestamp set when a reviewer approves the extraction;
   *  null until then. Distinct from `status` and `canonical.accepted`. */
  approved_at: string | null;
}

export interface ListExtractionsResponse {
  items: ExtractionStatusResponse[];
  total: number;
  page: number;
  page_size: number;
}

// ---------------------------------------------------------------------------
// Auth (Phase 4 step 5)
// ---------------------------------------------------------------------------

export interface UserDTO {
  id: string;
  email: string;
  full_name: string | null;
  locale: string;
  email_verified_at: string | null;
}

export interface OrganizationDTO {
  id: string;
  name: string;
  plan: string;
  monthly_extraction_quota: number;
  monthly_extractions_used: number;
  /** ISO 8601 UTC timestamp of the next rolling-window reset. */
  quota_reset_at: string;
}

export interface SessionResponse {
  user: UserDTO;
  organization: OrganizationDTO;
}

export type MeResponse = SessionResponse;

export interface RegisterRequest {
  email: string;
  password: string;
  full_name?: string;
  organization_name: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

/** Inner error body per Phase 3 §3.1. */
export interface ApiErrorBody {
  error: { code: string; message_en: string; message_ka: string };
}

/** Thrown by the API client on any 4xx/5xx response. */
export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly messageEn: string;
  readonly messageKa: string;

  constructor(
    status: number,
    code: string,
    messageEn: string,
    messageKa: string,
  ) {
    super(messageEn);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.messageEn = messageEn;
    this.messageKa = messageKa;
  }
}

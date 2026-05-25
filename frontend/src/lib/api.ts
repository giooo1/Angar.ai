/**
 * Thin client for the backend's HTTP API.
 * Configurable via NEXT_PUBLIC_API_URL; defaults to local dev backend.
 *
 * Every fetch sends `credentials: "include"` so the HttpOnly
 * angar_session cookie set by the backend travels with each request.
 *
 * Throws ApiError on any 4xx/5xx with the backend's bilingual error
 * envelope unpacked (Phase 3 §3.1: { error: { code, message_en, message_ka }}).
 */

import {
  ApiError,
  type ApiErrorBody,
  type ExtractionStatusResponse,
  type ListExtractionsResponse,
  type LoginRequest,
  type MeResponse,
  type RegisterRequest,
  type SessionResponse,
  type UploadResponse,
} from "./api-types";
import type { CanonicalInvoice } from "./canonical";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ??
  "http://localhost:8000";

const JSON_HEADERS = { "Content-Type": "application/json" };

async function unwrapError(res: Response): Promise<never> {
  let code = "UNKNOWN";
  let en = `HTTP ${res.status}`;
  let ka = en;
  try {
    const body = (await res.json()) as Partial<ApiErrorBody> & {
      detail?: Partial<ApiErrorBody>;
    };
    // FastAPI wraps ErrorResponse inside `detail` for HTTPException.
    const errBody = body.detail?.error ?? body.error;
    if (errBody) {
      code = errBody.code ?? code;
      en = errBody.message_en ?? en;
      ka = errBody.message_ka ?? ka;
    }
  } catch {
    // body wasn't JSON; fall through with HTTP defaults
  }
  throw new ApiError(res.status, code, en, ka);
}

// ---------------------------------------------------------------------------
// Auth (Phase 4 step 5)
// ---------------------------------------------------------------------------

export async function login(body: LoginRequest): Promise<SessionResponse> {
  const res = await fetch(`${API_BASE}/api/v1/auth/login`, {
    method: "POST",
    headers: JSON_HEADERS,
    body: JSON.stringify(body),
    credentials: "include",
  });
  if (!res.ok) await unwrapError(res);
  return (await res.json()) as SessionResponse;
}

export async function register(body: RegisterRequest): Promise<SessionResponse> {
  const res = await fetch(`${API_BASE}/api/v1/auth/register`, {
    method: "POST",
    headers: JSON_HEADERS,
    body: JSON.stringify(body),
    credentials: "include",
  });
  if (!res.ok) await unwrapError(res);
  return (await res.json()) as SessionResponse;
}

export async function logout(): Promise<void> {
  const res = await fetch(`${API_BASE}/api/v1/auth/logout`, {
    method: "POST",
    credentials: "include",
  });
  if (!res.ok) await unwrapError(res);
}

export async function me(signal?: AbortSignal): Promise<MeResponse> {
  const res = await fetch(`${API_BASE}/api/v1/me`, {
    signal,
    credentials: "include",
    cache: "no-store",
  });
  if (!res.ok) await unwrapError(res);
  return (await res.json()) as MeResponse;
}

export async function verifyEmail(token: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/v1/auth/verify-email`, {
    method: "POST",
    headers: JSON_HEADERS,
    body: JSON.stringify({ token }),
    credentials: "include",
  });
  if (!res.ok) await unwrapError(res);
}

export async function requestPasswordReset(email: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/v1/auth/request-password-reset`, {
    method: "POST",
    headers: JSON_HEADERS,
    body: JSON.stringify({ email }),
    credentials: "include",
  });
  if (!res.ok) await unwrapError(res);
}

export async function resetPassword(
  token: string,
  newPassword: string,
): Promise<SessionResponse> {
  const res = await fetch(`${API_BASE}/api/v1/auth/reset-password`, {
    method: "POST",
    headers: JSON_HEADERS,
    body: JSON.stringify({ token, new_password: newPassword }),
    credentials: "include",
  });
  if (!res.ok) await unwrapError(res);
  return (await res.json()) as SessionResponse;
}

// ---------------------------------------------------------------------------
// Billing (Phase 4.5 WS5)
// ---------------------------------------------------------------------------

export type Plan = "pro" | "business";

export async function createCheckoutSession(plan: Plan): Promise<{ url: string }> {
  const res = await fetch(`${API_BASE}/api/v1/billing/checkout`, {
    method: "POST",
    headers: JSON_HEADERS,
    body: JSON.stringify({ plan }),
    credentials: "include",
  });
  if (!res.ok) await unwrapError(res);
  return (await res.json()) as { url: string };
}

export async function createBillingPortalSession(): Promise<{ url: string }> {
  const res = await fetch(`${API_BASE}/api/v1/billing/portal`, {
    method: "POST",
    credentials: "include",
  });
  if (!res.ok) await unwrapError(res);
  return (await res.json()) as { url: string };
}

// ---------------------------------------------------------------------------
// Extraction (existing)
// ---------------------------------------------------------------------------

export async function uploadDocument(
  file: File,
  signal?: AbortSignal,
): Promise<UploadResponse> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API_BASE}/api/v1/documents`, {
    method: "POST",
    body: form,
    signal,
    credentials: "include",
  });
  if (!res.ok) await unwrapError(res);
  return (await res.json()) as UploadResponse;
}

export async function getExtraction(
  id: string,
  signal?: AbortSignal,
): Promise<ExtractionStatusResponse> {
  const res = await fetch(`${API_BASE}/api/v1/extractions/${id}`, {
    signal,
    credentials: "include",
  });
  if (!res.ok) await unwrapError(res);
  return (await res.json()) as ExtractionStatusResponse;
}

export async function reextract(
  documentId: string,
  signal?: AbortSignal,
): Promise<UploadResponse> {
  const res = await fetch(
    `${API_BASE}/api/v1/documents/${documentId}/extract`,
    { method: "POST", signal, credentials: "include" },
  );
  if (!res.ok) await unwrapError(res);
  return (await res.json()) as UploadResponse;
}

/** Mark an extraction as reviewed-and-approved. Idempotent server-side. */
export async function approveExtraction(
  extractionId: string,
  signal?: AbortSignal,
): Promise<ExtractionStatusResponse> {
  const res = await fetch(
    `${API_BASE}/api/v1/extractions/${extractionId}/approve`,
    { method: "POST", signal, credentials: "include" },
  );
  if (!res.ok) await unwrapError(res);
  return (await res.json()) as ExtractionStatusResponse;
}

/** Persist reviewer edits. The body is the full (edited) canonical; the
 *  backend validates it and stores it in `corrected_data` without touching
 *  the model's raw `canonical_data`. */
export async function saveCorrections(
  extractionId: string,
  corrected: CanonicalInvoice,
  signal?: AbortSignal,
): Promise<ExtractionStatusResponse> {
  const res = await fetch(
    `${API_BASE}/api/v1/extractions/${extractionId}/corrections`,
    {
      method: "PUT",
      headers: JSON_HEADERS,
      body: JSON.stringify(corrected),
      signal,
      credentials: "include",
    },
  );
  if (!res.ok) await unwrapError(res);
  return (await res.json()) as ExtractionStatusResponse;
}

export type ExportFormat = "csv" | "xlsx" | "json";

/**
 * Download an extraction's data in the given format. Fetches the blob (so a
 * 401/404 surfaces as an ApiError rather than navigating away, and binary
 * XLSX arrives intact), then triggers a synthetic download. `filename` is the
 * base name; the extension is appended from the format.
 */
export async function downloadExport(
  extractionId: string,
  format: ExportFormat,
  filename: string,
): Promise<void> {
  const res = await fetch(
    `${API_BASE}/api/v1/extractions/${extractionId}/export?format=${format}`,
    { credentials: "include" },
  );
  if (!res.ok) await unwrapError(res);
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${filename}.${format}`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

/** Soft-delete the documents behind the selected extractions. Returns the
 *  number of documents deleted. */
export async function bulkDeleteExtractions(
  extractionIds: string[],
): Promise<{ deleted: number }> {
  const res = await fetch(`${API_BASE}/api/v1/extractions/bulk-delete`, {
    method: "POST",
    headers: JSON_HEADERS,
    body: JSON.stringify({ extraction_ids: extractionIds }),
    credentials: "include",
  });
  if (!res.ok) await unwrapError(res);
  return (await res.json()) as { deleted: number };
}

/** Download the selected documents as one combined CSV (all line items). */
export async function downloadBulkCsv(extractionIds: string[]): Promise<void> {
  const res = await fetch(`${API_BASE}/api/v1/extractions/bulk-export`, {
    method: "POST",
    headers: JSON_HEADERS,
    body: JSON.stringify({ extraction_ids: extractionIds }),
    credentials: "include",
  });
  if (!res.ok) await unwrapError(res);
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "documents-export.csv";
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

/**
 * Poll `/extractions/{id}` until status becomes terminal or the timeout
 * fires. Cadence per Phase 3 §3.3: 2s for the first 30s, then 5s, abort
 * after 2 minutes.
 */
export async function pollExtraction(
  extractionId: string,
  onUpdate: (e: ExtractionStatusResponse) => void,
  signal?: AbortSignal,
): Promise<ExtractionStatusResponse> {
  const start = Date.now();
  let lastStatus: string | null = null;

  while (true) {
    if (signal?.aborted) throw new DOMException("aborted", "AbortError");
    const current = await getExtraction(extractionId, signal);
    if (current.status !== lastStatus) {
      lastStatus = current.status;
      onUpdate(current);
    }
    if (current.status === "completed" || current.status === "failed") {
      return current;
    }
    const elapsed = Date.now() - start;
    if (elapsed > 120_000) {
      // Two-minute "still working" timeout — surface as a synthetic failed.
      return { ...current, status: "failed", error_message: "poll timeout" };
    }
    const delay = elapsed < 30_000 ? 2_000 : 5_000;
    await new Promise((r) => setTimeout(r, delay));
  }
}

/** URL the iframe / <a> tag uses to fetch the original PDF for an upload. */
export function documentFileUrl(documentId: string): string {
  return `${API_BASE}/api/v1/documents/${documentId}/file`;
}

/**
 * Paginated list of extractions (org-scoped on the server side). Used by
 * the Review queue page at /review.
 */
export async function listExtractions(
  params: { page?: number; pageSize?: number } = {},
  signal?: AbortSignal,
): Promise<ListExtractionsResponse> {
  const qs = new URLSearchParams();
  if (params.page) qs.set("page", String(params.page));
  if (params.pageSize) qs.set("page_size", String(params.pageSize));
  const url = `${API_BASE}/api/v1/extractions${qs.size ? `?${qs}` : ""}`;
  const res = await fetch(url, {
    signal,
    cache: "no-store",
    credentials: "include",
  });
  if (!res.ok) await unwrapError(res);
  return (await res.json()) as ListExtractionsResponse;
}

export const apiBase = API_BASE;

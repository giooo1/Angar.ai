/**
 * Thin client for the backend's extraction-path API.
 * Configurable via NEXT_PUBLIC_API_URL; defaults to local dev backend.
 *
 * Throws ApiError on any 4xx/5xx with the backend's bilingual error
 * envelope unpacked (Phase 3 §3.1: { error: { code, message_en, message_ka }}).
 */

import {
  ApiError,
  type ApiErrorBody,
  type ExtractionStatusResponse,
  type UploadResponse,
} from "./api-types";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ??
  "http://localhost:8000";

async function unwrapError(res: Response): Promise<never> {
  let code = "UNKNOWN";
  let en = `HTTP ${res.status}`;
  let ka = en;
  try {
    const body = (await res.json()) as Partial<ApiErrorBody> & {
      detail?: Partial<ApiErrorBody>;
    };
    // FastAPI wraps the ErrorResponse inside `detail` for HTTPException.
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
  });
  if (!res.ok) await unwrapError(res);
  return (await res.json()) as UploadResponse;
}

export async function getExtraction(
  id: string,
  signal?: AbortSignal,
): Promise<ExtractionStatusResponse> {
  const res = await fetch(`${API_BASE}/api/v1/extractions/${id}`, { signal });
  if (!res.ok) await unwrapError(res);
  return (await res.json()) as ExtractionStatusResponse;
}

export async function reextract(
  documentId: string,
  signal?: AbortSignal,
): Promise<UploadResponse> {
  const res = await fetch(
    `${API_BASE}/api/v1/documents/${documentId}/extract`,
    { method: "POST", signal },
  );
  if (!res.ok) await unwrapError(res);
  return (await res.json()) as UploadResponse;
}

/**
 * Poll `/extractions/{id}` until status becomes terminal or the timeout
 * fires. Cadence per Phase 3 §3.3: 2s for the first 30s, then 5s, abort
 * after 2 minutes.
 *
 * `onUpdate` fires for every status change including the initial fetch.
 * Returns the terminal extraction state (status = "completed" | "failed").
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

export const apiBase = API_BASE;

/**
 * Frontend helpers for the per-field confidence scores the backend
 * persists on `Extraction.field_confidence` (WS2). Pairs with
 * `<ConfidenceRow>` and the other review blocks.
 *
 * The review screen uses a two-axis state model: presence (is the field
 * on the document?) is separate from confidence (did the model read it
 * surely?). The backend already encodes presence in the score
 * (`backend/confidence.py`): 0.0 means null/missing, 0.40 present-but-junk,
 * 0.85/1.0 present & good. We derive a calm three-state model from the
 * value plus the score so a field that's simply blank on the invoice reads
 * neutral grey ("not on document"), never red.
 *
 *   verified — present and confident (score ≥ 0.85, user-confirmed, or
 *              unscored legacy data); calm, green ✓.
 *   check    — present but the model is unsure (score < 0.85); amber, %.
 *   empty    — absent/blank on the document; neutral grey.
 *
 * The "user-confirmed" flag is UI-only: clicking a check/empty chip marks
 * the field as personally checked. We persist that in localStorage keyed by
 * `extraction_id + field_path` so it survives navigation and reloads.
 */

export type FieldState = "verified" | "check" | "empty";

/** At or above this score a present field is treated as verified (calm). */
export const VERIFIED_THRESHOLD = 0.85;

/**
 * Whether a field carries a real value. Null/undefined and empty-after-trim
 * are absent; backend "suspicious" placeholders (e.g. "N/A", "—") still count
 * as present so the reviewer sees and can fix them.
 */
export function isPresent(value: unknown): boolean {
  if (value === null || value === undefined) return false;
  return String(value).trim() !== "";
}

/**
 * Derive a field's visual state from its presence, confidence score, and the
 * user-confirmed flag. Present-but-unscored (legacy extractions) defaults to
 * the calm "verified" rather than alarming.
 */
export function fieldState(
  present: boolean,
  score: number | undefined,
  confirmed: boolean,
): FieldState {
  // An explicit user confirmation always wins — including confirming that a
  // blank field is correctly absent.
  if (confirmed) return "verified";
  if (!present) return "empty";
  if (score === undefined) return "verified";
  return score >= VERIFIED_THRESHOLD ? "verified" : "check";
}

export function formatPct(score: number | undefined): string {
  if (score === undefined) return "—";
  return `${Math.round(score * 100)}%`;
}

export function meanConfidence(scores: Record<string, number>): number | null {
  const values = Object.values(scores);
  if (values.length === 0) return null;
  return values.reduce((acc, v) => acc + v, 0) / values.length;
}

// ---------------------------------------------------------------------------
// Verified-toggle persistence (localStorage)
// ---------------------------------------------------------------------------

const LS_PREFIX = "angar:verified";

function key(extractionId: string, fieldPath: string): string {
  return `${LS_PREFIX}:${extractionId}:${fieldPath}`;
}

export function isVerified(extractionId: string, fieldPath: string): boolean {
  if (typeof window === "undefined") return false;
  try {
    return window.localStorage.getItem(key(extractionId, fieldPath)) === "1";
  } catch {
    return false;
  }
}

export function setVerified(
  extractionId: string,
  fieldPath: string,
  verified: boolean,
): void {
  if (typeof window === "undefined") return;
  try {
    const k = key(extractionId, fieldPath);
    if (verified) window.localStorage.setItem(k, "1");
    else window.localStorage.removeItem(k);
  } catch {
    // Quota exceeded or storage disabled — silently degrade.
  }
}

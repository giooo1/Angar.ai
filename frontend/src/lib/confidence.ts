/**
 * Frontend helpers for the per-field confidence scores the backend now
 * persists on `Extraction.field_confidence` (WS2). Pairs with
 * `<ConfidenceRow>` in the Review v2 UI.
 *
 * Score bands (synced with `backend/confidence.py`):
 *   1.00       perfect    — high
 *   0.85       format off — high
 *   0.70       cross-check fail — med
 *   0.40       suspicious — low
 *   0.00       missing — low
 *
 * Frontend bins:
 *   ≥ 0.85   high (calm, score chip)
 *   0.60–0.84 med  (yellow tint + score chip)
 *   < 0.60   low  (red tint + ! badge)
 *
 * The "verified" tier is a UI-only state — the user clicks a score
 * chip to mark a field as personally checked. We persist that flag in
 * localStorage keyed by `extraction_id + field_path` so navigating
 * away and back doesn't clear it, and so the next page render shows
 * the same Verified affordance.
 */

export type ConfidenceBucket = "high" | "med" | "low" | "verified" | "unknown";

export function bucket(score: number | undefined): ConfidenceBucket {
  if (score === undefined) return "unknown";
  if (score >= 0.85) return "high";
  if (score >= 0.60) return "med";
  return "low";
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

export function countByBucket(
  scores: Record<string, number>,
): { high: number; med: number; low: number } {
  let high = 0;
  let med = 0;
  let low = 0;
  for (const v of Object.values(scores)) {
    const b = bucket(v);
    if (b === "high") high++;
    else if (b === "med") med++;
    else if (b === "low") low++;
  }
  return { high, med, low };
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

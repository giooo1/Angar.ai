/**
 * Frontend helpers for the per-field confidence scores the backend persists
 * on `Extraction.field_confidence`.
 *
 * Display model (the review pane only surfaces confidence when a field is
 * below 90%):
 *   ≥ 0.90   ok      — show nothing
 *   0.80–0.89 warn   — amber icon + "· NN%" inline by the label
 *   < 0.80   danger  — red icon, label + value in danger; value "Missing" if null
 */

export type ConfidenceLevel = "ok" | "warn" | "danger";

export function confidenceLevel(score: number | undefined): ConfidenceLevel {
  if (score === undefined) return "danger";
  if (score >= 0.9) return "ok";
  if (score >= 0.8) return "warn";
  return "danger";
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

/** Count of scored fields below 90% — drives the header subtitle. */
export function countNeedsReview(scores: Record<string, number>): number {
  return Object.values(scores).filter((v) => v < 0.9).length;
}

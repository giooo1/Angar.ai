"use client";

import { useEffect, useState } from "react";

import { cn } from "@/lib/utils";
import {
  bucket,
  formatPct,
  isVerified,
  setVerified,
  type ConfidenceBucket,
} from "@/lib/confidence";
import { commitText, useReviewEdit } from "./review-edit-context";

type Props = {
  /** Short uppercase label rendered on the left. */
  label: string;
  /** Display value. Renders as monospace by default. */
  value: React.ReactNode;
  /** Confidence ∈ [0, 1] from `field_confidence`. `undefined` → no chip. */
  confidence?: number;
  /** Dotted-path key, e.g. `seller.tin`. Used for localStorage Verified flag. */
  fieldPath: string;
  /** Extraction id for the localStorage key. */
  extractionId: string;
  /** Optional Tailwind classes for the value (e.g. `geo` italic). */
  valueClassName?: string;
  /** When true the row spans the value column full-width (no chip column). */
  full?: boolean;
  /** Set false for enum/derived values that can't be safely edited as free
   *  text (e.g. party_type renders a label, not the stored value). */
  editable?: boolean;
};

/**
 * Universal field row for Review v2.
 *
 * Visual states keyed off `bucket(confidence)`:
 *   - high       → calm, score chip with %
 *   - med        → yellow tint + ! badge + score chip
 *   - low        → red tint + ! badge + score chip
 *   - verified   → user has clicked the chip; row forced to high tint,
 *                  chip reads "Verified"
 *   - unknown    → no chip rendered (old extraction without scores)
 *
 * Click the score chip to toggle verified. State persists to localStorage
 * via `setVerified(extractionId, fieldPath)`.
 */
export function ConfidenceRow({
  label,
  value,
  confidence,
  fieldPath,
  extractionId,
  valueClassName,
  full,
  editable = true,
}: Props) {
  const [verified, setVerifiedState] = useState(false);
  const edit = useReviewEdit();
  const canEdit = editable && edit.editable;

  useEffect(() => {
    setVerifiedState(isVerified(extractionId, fieldPath));
  }, [extractionId, fieldPath]);

  const effectiveBucket: ConfidenceBucket = verified ? "verified" : bucket(confidence);

  const onToggle = () => {
    const next = !verified;
    setVerified(extractionId, fieldPath, next);
    setVerifiedState(next);
  };

  return (
    <div
      className={cn(
        "relative grid items-center gap-3 border-b border-line-2 last:border-b-0 transition-colors",
        full ? "grid-cols-[120px_1fr]" : "grid-cols-[120px_1fr_100px]",
        "py-2",
        effectiveBucket === "med" &&
          "bg-gradient-to-r from-warn-soft via-warn-soft/40 to-transparent",
        effectiveBucket === "low" &&
          "bg-gradient-to-r from-error-soft via-error-soft/55 to-transparent",
        effectiveBucket === "med" || effectiveBucket === "low" ? "pl-[30px] pr-3.5" : "px-3.5",
      )}
    >
      {(effectiveBucket === "med" || effectiveBucket === "low") && (
        <SeverityBadge level={effectiveBucket} />
      )}
      {effectiveBucket === "med" && (
        <span className="absolute left-0 top-0 bottom-0 w-[3px] bg-warn" aria-hidden="true" />
      )}
      {effectiveBucket === "low" && (
        <span className="absolute left-0 top-0 bottom-0 w-[3px] bg-error" aria-hidden="true" />
      )}

      <span className="font-mono text-[10px] text-ink-3 tracking-[0.07em] uppercase font-medium">
        {label}
      </span>

      <span
        className={cn(
          "font-mono text-[13px] text-ink font-medium tracking-[-0.005em] px-2 py-1 rounded-md border border-transparent outline-none cursor-text transition-colors min-w-0 overflow-hidden text-ellipsis",
          "hover:border-line-2 focus:border-accent focus:bg-paper focus:shadow-[0_0_0_3px_var(--color-accent-soft)] focus:whitespace-normal focus:overflow-visible",
          effectiveBucket === "low" && "border-error/25",
          valueClassName,
        )}
        contentEditable={canEdit}
        suppressContentEditableWarning
        onBlur={
          canEdit
            ? (e) => edit.updateField(fieldPath, commitText(e.currentTarget.textContent ?? ""))
            : undefined
        }
      >
        {value}
      </span>

      {!full && (
        <ScoreChip bucket={effectiveBucket} score={confidence} onClick={onToggle} />
      )}
    </div>
  );
}

function SeverityBadge({ level }: { level: "med" | "low" }) {
  return (
    <span
      className={cn(
        "absolute left-[14px] top-1/2 -translate-x-1/2 -translate-y-1/2 w-[18px] h-[18px] rounded-full inline-flex items-center justify-center font-mono font-bold text-[11px] z-[2]",
        level === "med" && "bg-paper border-[1.5px] border-warn text-warn",
        level === "low" && "bg-error border-[1.5px] border-error text-white",
      )}
      aria-hidden="true"
    >
      !
    </span>
  );
}

function ScoreChip({
  bucket: b,
  score,
  onClick,
}: {
  bucket: ConfidenceBucket;
  score: number | undefined;
  onClick: () => void;
}) {
  if (b === "unknown") {
    return <span className="font-mono text-[10.5px] text-ink-4 tracking-[0.04em] text-right">—</span>;
  }
  return (
    <button
      type="button"
      onClick={onClick}
      title={b === "verified" ? "Click to unverify" : "Click to mark verified"}
      className={cn(
        "inline-flex items-center gap-1.5 px-2 py-1 rounded-md border font-mono font-semibold tracking-[0.02em] justify-end min-w-[84px] cursor-pointer transition-[filter] hover:brightness-95",
        b === "high" && "bg-accent-soft text-accent border-accent/20 text-[10.5px]",
        b === "med" && "bg-warn-soft text-[#7a5a13] border-warn/30 text-[10.5px]",
        b === "low" && "bg-error-soft text-[#7a201d] border-error/30 text-[10.5px]",
        b === "verified" &&
          "bg-paper text-accent border-accent/30 uppercase text-[9.5px] tracking-[0.05em]",
      )}
    >
      {b === "verified" ? (
        <>
          <span className="font-bold text-accent-2">✓</span>
          <span>Verified</span>
        </>
      ) : (
        <span>{formatPct(score)}</span>
      )}
    </button>
  );
}

"use client";

import { cn } from "@/lib/utils";
import { confidenceLevel, formatPct } from "@/lib/confidence";
import { AlertCircleIcon, AlertTriangleIcon } from "@/components/ui/icons";
import { commitText, useReviewEdit } from "./review-edit-context";

type Props = {
  /** Sentence-case label. */
  label: string;
  /** Display value; null/empty renders "Missing" (danger) or "—". */
  value: string | null;
  /** Dotted-path key, e.g. "seller.tin". */
  fieldPath: string;
  /** Confidence ∈ [0,1]. Only surfaced when < 0.90. */
  confidence?: number;
  valueClassName?: string;
  editable?: boolean;
  /** Tabular-nums for IDs (TIN, document number) so digits align. */
  numeric?: boolean;
};

/**
 * Flat field: sentence-case label above the value, no card, no pill.
 *
 * Confidence is shown only when a field is below 90%: an amber triangle +
 * "· NN%" by the label for 80–89%, or a red circle with the label + value in
 * danger for <80% (value reads "Missing" when empty). Values stay
 * click-to-edit (uncontrolled `contentEditable`, committed on blur).
 */
export function ConfidenceRow({
  label,
  value,
  fieldPath,
  confidence,
  valueClassName,
  editable = true,
  numeric,
}: Props) {
  const edit = useReviewEdit();
  const canEdit = editable && edit.editable;

  const level = confidenceLevel(confidence);
  const danger = confidence !== undefined && level === "danger";
  const warn = confidence !== undefined && level === "warn";
  const isEmpty = value == null || value === "" || value === "—";
  const displayValue = isEmpty ? (danger ? "Missing" : "—") : value;

  return (
    <div className="min-w-0">
      <div
        className={cn(
          "flex items-center gap-1 text-[11px] mb-0.5 leading-tight",
          danger ? "text-error" : "text-ink-2",
        )}
      >
        <span>{label}</span>
        {warn && (
          <span className="inline-flex items-center gap-0.5 text-warn font-medium">
            <AlertTriangleIcon size={11} /> · {formatPct(confidence)}
          </span>
        )}
        {danger && confidence !== undefined && (
          <span className="inline-flex items-center gap-0.5 text-error font-medium">
            <AlertCircleIcon size={11} /> · {formatPct(confidence)}
          </span>
        )}
      </div>
      <div
        className={cn(
          "text-[14px] font-normal text-ink rounded px-1 -mx-1 py-0.5 outline-none cursor-text transition-colors",
          "hover:bg-bg-2/60 focus:bg-paper-2 focus:shadow-[0_0_0_2px_var(--color-accent-soft)]",
          numeric && "[font-variant-numeric:tabular-nums]",
          isEmpty && !danger && "text-ink-4",
          danger && "text-error",
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
        {displayValue}
      </div>
    </div>
  );
}

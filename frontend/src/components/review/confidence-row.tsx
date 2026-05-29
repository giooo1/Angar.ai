"use client";

import { cn } from "@/lib/utils";
import { fieldState, isPresent } from "@/lib/confidence";
import { commitText, useReviewEdit } from "./review-edit-context";
import { StateChip, useConfirmed } from "./field-state-ui";

type Props = {
  /** Short uppercase label rendered on the left. */
  label: string;
  /** Display value. Renders as monospace by default. Null/blank → "empty". */
  value: React.ReactNode;
  /** Confidence ∈ [0, 1] from `field_confidence`. */
  confidence?: number;
  /** Dotted-path key, e.g. `seller.tin`. Used for the localStorage flag. */
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
  /** Override presence detection (e.g. when `value` is a derived label). */
  present?: boolean;
};

/**
 * Universal field row. Two-axis state via `fieldState`:
 *   - verified → calm, green ✓ chip
 *   - check    → amber tint + left bar + % chip
 *   - empty    → neutral grey, muted "not on document" placeholder
 *
 * Click the chip to confirm (or unconfirm) the field; the flag persists to
 * localStorage via `useConfirmed`.
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
  present,
}: Props) {
  const { confirmed, toggle } = useConfirmed(extractionId, fieldPath);
  const edit = useReviewEdit();
  const canEdit = editable && edit.editable;

  const isThere = present ?? isPresent(value);
  const state = fieldState(isThere, confidence, confirmed);

  return (
    <div
      className={cn(
        "relative grid items-center gap-3 border-b border-line-2 last:border-b-0 transition-colors py-2",
        full ? "grid-cols-[120px_1fr]" : "grid-cols-[120px_1fr_100px]",
        state === "check"
          ? "bg-gradient-to-r from-warn-soft via-warn-soft/40 to-transparent pl-[18px] pr-3.5"
          : "px-3.5",
      )}
    >
      {state === "check" && (
        <span className="absolute left-0 top-0 bottom-0 w-[3px] bg-warn" aria-hidden="true" />
      )}

      <span className="font-mono text-[10px] text-ink-3 tracking-[0.07em] uppercase font-medium">
        {label}
      </span>

      <span
        className={cn(
          "font-mono text-[13px] text-ink font-medium tracking-[-0.005em] px-2 py-1 rounded-md border border-transparent outline-none cursor-text transition-colors min-w-0 overflow-hidden text-ellipsis",
          "hover:border-line-2 focus:border-accent focus:bg-paper focus:shadow-[0_0_0_3px_var(--color-accent-soft)] focus:whitespace-normal focus:overflow-visible",
          state === "empty" &&
            "text-ink-4 italic empty:before:content-['not_on_document'] empty:before:text-ink-4",
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
        {state === "empty" ? null : value}
      </span>

      {!full && (
        <StateChip
          state={state}
          score={confidence}
          confirmed={confirmed}
          onToggle={toggle}
          className="justify-end min-w-[84px]"
        />
      )}
    </div>
  );
}

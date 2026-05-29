"use client";

import { cn } from "@/lib/utils";
import { fieldState, isPresent } from "@/lib/confidence";
import { commitText, useReviewEdit } from "./review-edit-context";
import { StateChip, useConfirmed } from "./field-state-ui";
import { SectionBlock } from "./section-block";

type Props = {
  extractionId: string;
  documentNumber: string | null;
  documentDate: string | null;
  currency: string;
  confidence: Record<string, number>;
};

/**
 * 3-column inline strip: Number / Date / Currency. Each cell stacks
 * label above value above a small state chip; a low-confidence cell gets
 * a top-banded amber strip, a blank field reads neutral "not on document".
 */
export function DocumentStrip({
  extractionId,
  documentNumber,
  documentDate,
  currency,
  confidence,
}: Props) {
  return (
    <SectionBlock letter="D" title="Document">
      <div className="grid grid-cols-3 divide-x divide-line-2">
        <Cell
          extractionId={extractionId}
          fieldPath="document_number"
          label="Number"
          value={documentNumber}
          confidence={confidence["document_number"]}
        />
        <Cell
          extractionId={extractionId}
          fieldPath="document_date"
          label="Date"
          value={documentDate}
          confidence={confidence["document_date"]}
        />
        <Cell
          extractionId={extractionId}
          fieldPath="document_currency"
          label="Currency"
          value={currency}
          confidence={confidence["document_currency"]}
        />
      </div>
    </SectionBlock>
  );
}

function Cell({
  extractionId,
  fieldPath,
  label,
  value,
  confidence,
}: {
  extractionId: string;
  fieldPath: string;
  label: string;
  value: string | null;
  confidence?: number;
}) {
  const { confirmed, toggle } = useConfirmed(extractionId, fieldPath);
  const edit = useReviewEdit();

  const state = fieldState(isPresent(value), confidence, confirmed);

  return (
    <div
      className={cn(
        "relative px-3.5 py-2.5 flex flex-col gap-1",
        state === "check" && "bg-gradient-to-b from-warn-soft to-transparent",
      )}
    >
      {state === "check" && (
        <span className="absolute left-0 top-0 h-[3px] w-full bg-warn" aria-hidden="true" />
      )}
      <span className="font-mono text-[9.5px] text-ink-3 tracking-[0.07em] uppercase font-medium">
        {label}
      </span>
      <span
        className={cn(
          "font-mono text-[14.5px] text-ink font-medium tracking-[-0.005em] px-1.5 py-[1px] rounded-md border border-transparent hover:border-line-2 focus:border-accent focus:bg-paper outline-none cursor-text",
          state === "empty" &&
            "text-ink-4 italic empty:before:content-['not_on_document'] empty:before:text-ink-4",
        )}
        contentEditable={edit.editable}
        suppressContentEditableWarning
        onBlur={
          edit.editable
            ? (e) => edit.updateField(fieldPath, commitText(e.currentTarget.textContent ?? ""))
            : undefined
        }
      >
        {state === "empty" ? null : value}
      </span>
      <StateChip
        state={state}
        score={confidence}
        confirmed={confirmed}
        onToggle={toggle}
        className="self-start"
      />
    </div>
  );
}

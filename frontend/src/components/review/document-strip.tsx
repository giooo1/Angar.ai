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
 * label above value above a small score chip; confidence-low cells
 * get a top-banded red strip.
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
          value={documentNumber ?? "—"}
          confidence={confidence["document_number"]}
        />
        <Cell
          extractionId={extractionId}
          fieldPath="document_date"
          label="Date"
          value={documentDate ?? "—"}
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
  value: string;
  confidence?: number;
}) {
  const [verified, setVerifiedState] = useState(false);
  const edit = useReviewEdit();

  useEffect(() => {
    setVerifiedState(isVerified(extractionId, fieldPath));
  }, [extractionId, fieldPath]);

  const b: ConfidenceBucket = verified ? "verified" : bucket(confidence);

  const onToggle = () => {
    const next = !verified;
    setVerified(extractionId, fieldPath, next);
    setVerifiedState(next);
  };

  return (
    <div
      className={cn(
        "relative px-4 py-3.5 flex flex-col gap-1.5",
        b === "med" && "bg-gradient-to-b from-warn-soft to-transparent",
        b === "low" && "bg-gradient-to-b from-error-soft to-transparent",
      )}
    >
      {(b === "med" || b === "low") && (
        <span
          className={cn(
            "absolute left-0 top-0 h-[3px] w-full",
            b === "med" ? "bg-warn" : "bg-error",
          )}
          aria-hidden="true"
        />
      )}
      <span className="font-mono text-[9.5px] text-ink-3 tracking-[0.07em] uppercase font-medium">
        {label}
      </span>
      <span
        className="font-mono text-[14.5px] text-ink font-medium tracking-[-0.005em] px-1.5 py-[1px] rounded-md border border-transparent hover:border-line-2 focus:border-accent focus:bg-paper outline-none cursor-text"
        contentEditable={edit.editable}
        suppressContentEditableWarning
        onBlur={
          edit.editable
            ? (e) => edit.updateField(fieldPath, commitText(e.currentTarget.textContent ?? ""))
            : undefined
        }
      >
        {value}
      </span>
      <button
        type="button"
        onClick={onToggle}
        title={b === "verified" ? "Click to unverify" : "Click to mark verified"}
        className={cn(
          "self-start inline-flex items-center gap-1.5 px-2 py-[3px] rounded-md border font-mono font-semibold tracking-[0.02em] cursor-pointer transition-[filter] hover:brightness-95",
          b === "high" && "bg-accent-soft text-accent border-accent/20 text-[10.5px]",
          b === "med" && "bg-warn-soft text-[#7a5a13] border-warn/30 text-[10.5px]",
          b === "low" && "bg-error-soft text-[#7a201d] border-error/30 text-[10.5px]",
          b === "verified" &&
            "bg-paper text-accent border-accent/30 uppercase text-[9.5px] tracking-[0.05em]",
          b === "unknown" && "bg-paper-2 text-ink-3 border-line-2 text-[10.5px]",
        )}
      >
        {b === "verified" ? (
          <>
            <span className="font-bold text-accent-2">✓</span>
            <span>Verified</span>
          </>
        ) : (
          <span>{formatPct(confidence)}</span>
        )}
      </button>
    </div>
  );
}

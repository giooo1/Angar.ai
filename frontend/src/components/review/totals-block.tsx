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
import type { Money } from "@/lib/canonical";
import { commitText, useReviewEdit } from "./review-edit-context";
import { SectionBlock } from "./section-block";

type Props = {
  extractionId: string;
  subtotal: Money | null;
  vat: Money | null;
  discount: Money | null;
  shipping: Money | null;
  grand: Money | null;
  confidence: Record<string, number>;
};

/**
 * Right-aligned totals block. Standard rows for Subtotal / VAT,
 * muted rows for null Shipping / Discount, and a big Grand total row
 * at the bottom. Each amount has its own confidence chip.
 */
export function TotalsBlock({
  extractionId,
  subtotal,
  vat,
  discount,
  shipping,
  grand,
  confidence,
}: Props) {
  return (
    <SectionBlock letter="Σ" title="Totals" bodyClassName="py-1.5">
      <AmountRow
        extractionId={extractionId}
        fieldPath="subtotal_total.amount"
        label="Subtotal"
        money={subtotal}
        confidence={confidence["subtotal_total.amount"]}
      />
      <AmountRow
        extractionId={extractionId}
        fieldPath="vat_total.amount"
        label="VAT"
        money={vat}
        confidence={confidence["vat_total.amount"]}
      />
      <MutedRow label="Shipping" money={shipping} />
      <MutedRow label="Discount" money={discount} />
      <GrandRow
        extractionId={extractionId}
        fieldPath="grand_total.amount"
        money={grand}
        confidence={confidence["grand_total.amount"]}
      />
    </SectionBlock>
  );
}

function MoneyText({ money }: { money: Money | null }) {
  if (!money) return <span className="text-ink-4">—</span>;
  return (
    <span>
      {money.amount} <span className="text-ink-3">{money.currency}</span>
    </span>
  );
}

function AmountRow({
  extractionId,
  fieldPath,
  label,
  money,
  confidence,
}: {
  extractionId: string;
  fieldPath: string;
  label: string;
  money: Money | null;
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
        "grid grid-cols-[1fr_auto_auto] items-center gap-3.5 px-4 py-2 font-mono text-[12px]",
        b === "med" &&
          "bg-gradient-to-r from-warn-soft to-transparent border-l-[3px] border-warn pl-[15px]",
        b === "low" &&
          "bg-gradient-to-r from-error-soft to-transparent border-l-[3px] border-error pl-[15px]",
      )}
    >
      <span className="text-[10px] text-ink-3 tracking-[0.07em] uppercase font-medium">
        {label}
      </span>
      <span className="text-ink font-medium text-right">
        <EditableAmount money={money} fieldPath={fieldPath} edit={edit} />
      </span>
      <Chip bucket={b} score={confidence} onClick={onToggle} />
    </div>
  );
}

/**
 * The amount portion of a money cell, editable on its own; the currency code
 * sits beside it as a static suffix so a blur capture reads just the number.
 * A null money renders a non-editable "—".
 */
function EditableAmount({
  money,
  fieldPath,
  edit,
}: {
  money: Money | null;
  fieldPath: string;
  edit: ReturnType<typeof useReviewEdit>;
}) {
  if (!money) return <span className="text-ink-4">—</span>;
  return (
    <>
      <span
        className="outline-none cursor-text rounded px-0.5 focus:bg-paper focus:shadow-[0_0_0_3px_var(--color-accent-soft)]"
        contentEditable={edit.editable}
        suppressContentEditableWarning
        onBlur={
          edit.editable
            ? (e) => edit.updateField(fieldPath, commitText(e.currentTarget.textContent ?? ""))
            : undefined
        }
      >
        {money.amount}
      </span>{" "}
      <span className="text-ink-3">{money.currency}</span>
    </>
  );
}

function MutedRow({ label, money }: { label: string; money: Money | null }) {
  return (
    <div className="grid grid-cols-[1fr_auto_auto] items-center gap-3.5 px-4 py-2 font-mono text-[12px] text-ink-4">
      <span className="text-[10px] text-ink-3 tracking-[0.07em] uppercase font-medium">
        {label}
      </span>
      <span className="text-right">
        <MoneyText money={money} />
      </span>
      <span aria-hidden="true" />
    </div>
  );
}

function GrandRow({
  extractionId,
  fieldPath,
  money,
  confidence,
}: {
  extractionId: string;
  fieldPath: string;
  money: Money | null;
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
    <div className="mt-1.5 grid grid-cols-[1fr_auto_auto] items-center gap-3.5 px-4 py-3.5 border-t border-line-2 bg-paper-2">
      <span className="font-mono text-[11px] text-ink font-semibold tracking-[0.06em] uppercase">
        Grand total
      </span>
      <span className="font-serif text-[22px] font-medium tracking-[-0.02em] text-ink text-right">
        {money ? (
          <>
            <span
              className="outline-none cursor-text rounded px-0.5 focus:bg-paper focus:shadow-[0_0_0_3px_var(--color-accent-soft)]"
              contentEditable={edit.editable}
              suppressContentEditableWarning
              onBlur={
                edit.editable
                  ? (e) => edit.updateField(fieldPath, commitText(e.currentTarget.textContent ?? ""))
                  : undefined
              }
            >
              {money.amount}
            </span>
            <span className="text-[12px] text-ink-3 font-mono font-normal ml-1.5">
              {money.currency}
            </span>
          </>
        ) : (
          <span className="text-ink-4">—</span>
        )}
      </span>
      <Chip bucket={b} score={confidence} onClick={onToggle} />
    </div>
  );
}

function Chip({
  bucket: b,
  score,
  onClick,
}: {
  bucket: ConfidenceBucket;
  score: number | undefined;
  onClick: () => void;
}) {
  if (b === "unknown") {
    return <span className="font-mono text-[10.5px] text-ink-4 min-w-[60px] text-right">—</span>;
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

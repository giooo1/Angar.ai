"use client";

import { cn } from "@/lib/utils";
import { fieldState, isPresent } from "@/lib/confidence";
import type { Money } from "@/lib/canonical";
import { commitText, useReviewEdit } from "./review-edit-context";
import { StateChip, useConfirmed } from "./field-state-ui";
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
 * at the bottom. Each amount carries its own two-axis state chip; a total
 * that's simply not on the document reads neutral "not on document".
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

function EmptyAmount() {
  return <span className="text-ink-4 italic">not on document</span>;
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
  const { confirmed, toggle } = useConfirmed(extractionId, fieldPath);
  const edit = useReviewEdit();
  const present = !!money && isPresent(money.amount);
  const state = fieldState(present, confidence, confirmed);

  return (
    <div
      className={cn(
        "grid grid-cols-[1fr_auto_auto] items-center gap-3.5 px-3.5 py-1.5 font-mono text-[12px]",
        state === "check" &&
          "bg-gradient-to-r from-warn-soft to-transparent border-l-[3px] border-warn pl-[15px]",
      )}
    >
      <span className="text-[10px] text-ink-3 tracking-[0.07em] uppercase font-medium">
        {label}
      </span>
      <span className="text-ink font-medium text-right">
        {money ? <EditableAmount money={money} fieldPath={fieldPath} edit={edit} /> : <EmptyAmount />}
      </span>
      <StateChip
        state={state}
        score={confidence}
        confirmed={confirmed}
        onToggle={toggle}
        className="justify-end min-w-[84px]"
      />
    </div>
  );
}

/**
 * The amount portion of a money cell, editable on its own; the currency code
 * sits beside it as a static suffix so a blur capture reads just the number.
 */
function EditableAmount({
  money,
  fieldPath,
  edit,
}: {
  money: Money;
  fieldPath: string;
  edit: ReturnType<typeof useReviewEdit>;
}) {
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
    <div className="grid grid-cols-[1fr_auto_auto] items-center gap-3.5 px-3.5 py-1.5 font-mono text-[12px] text-ink-4">
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
  const { confirmed, toggle } = useConfirmed(extractionId, fieldPath);
  const edit = useReviewEdit();
  const present = !!money && isPresent(money.amount);
  const state = fieldState(present, confidence, confirmed);

  return (
    <div className="mt-1 grid grid-cols-[1fr_auto_auto] items-center gap-3.5 px-3.5 py-2.5 border-t border-line-2 bg-paper-2">
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
          <span className="text-[14px] font-mono italic text-ink-4">not on document</span>
        )}
      </span>
      <StateChip
        state={state}
        score={confidence}
        confirmed={confirmed}
        onToggle={toggle}
        className="justify-end min-w-[84px]"
      />
    </div>
  );
}

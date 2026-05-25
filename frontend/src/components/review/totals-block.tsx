"use client";

import { cn } from "@/lib/utils";
import { confidenceLevel, formatPct } from "@/lib/confidence";
import type { Money } from "@/lib/canonical";
import { AlertCircleIcon, AlertTriangleIcon } from "@/components/ui/icons";
import { commitText, useReviewEdit } from "./review-edit-context";
import { SectionHeader } from "./section-header";

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
 * Flat totals: Subtotal / VAT, muted Shipping / Discount, then a larger Grand
 * total. Amounts are click-to-edit (the amount only; currency is a static
 * suffix); confidence surfaces by the label when below 90%.
 */
export function TotalsBlock({ subtotal, vat, discount, shipping, grand, confidence }: Props) {
  return (
    <section>
      <SectionHeader label="Totals" />
      <div className="flex flex-col gap-2">
        <AmountRow label="Subtotal" money={subtotal} fieldPath="subtotal_total.amount" confidence={confidence["subtotal_total.amount"]} />
        <AmountRow label="VAT" money={vat} fieldPath="vat_total.amount" confidence={confidence["vat_total.amount"]} />
        <MutedRow label="Shipping" money={shipping} />
        <MutedRow label="Discount" money={discount} />
        <AmountRow label="Grand total" money={grand} fieldPath="grand_total.amount" confidence={confidence["grand_total.amount"]} grand />
      </div>
    </section>
  );
}

function ConfLabel({ label, confidence }: { label: string; confidence?: number }) {
  const level = confidenceLevel(confidence);
  const danger = confidence !== undefined && level === "danger";
  const warn = confidence !== undefined && level === "warn";
  return (
    <span className={cn("inline-flex items-center gap-1 text-[11px]", danger ? "text-error" : "text-ink-2")}>
      {label}
      {warn && (
        <span className="inline-flex items-center gap-0.5 text-warn font-medium">
          <AlertTriangleIcon size={11} /> · {formatPct(confidence)}
        </span>
      )}
      {danger && (
        <span className="inline-flex items-center gap-0.5 text-error font-medium">
          <AlertCircleIcon size={11} /> · {formatPct(confidence)}
        </span>
      )}
    </span>
  );
}

function AmountRow({
  label,
  money,
  fieldPath,
  confidence,
  grand,
}: {
  label: string;
  money: Money | null;
  fieldPath: string;
  confidence?: number;
  grand?: boolean;
}) {
  const edit = useReviewEdit();
  const danger = confidence !== undefined && confidenceLevel(confidence) === "danger";

  return (
    <div
      className={cn(
        "flex items-baseline justify-between gap-3",
        grand && "mt-1 pt-2.5 border-t border-line-2",
      )}
    >
      <ConfLabel label={label} confidence={confidence} />
      <span
        className={cn(
          "text-right [font-variant-numeric:tabular-nums] text-ink",
          grand ? "font-serif text-[20px] tracking-[-0.01em]" : "text-[14px]",
          danger && "text-error",
        )}
      >
        {money ? (
          <>
            <span
              className="outline-none cursor-text rounded px-0.5 focus:bg-paper-2 focus:shadow-[0_0_0_2px_var(--color-accent-soft)]"
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
            <span className={cn("text-ink-3 ml-1", grand ? "text-[12px]" : "text-[12px]")}>
              {money.currency}
            </span>
          </>
        ) : (
          <span className={danger ? "text-error" : "text-ink-4"}>{danger ? "Missing" : "—"}</span>
        )}
      </span>
    </div>
  );
}

function MutedRow({ label, money }: { label: string; money: Money | null }) {
  return (
    <div className="flex items-baseline justify-between gap-3 text-ink-4">
      <span className="text-[11px]">{label}</span>
      <span className="text-[14px] text-right [font-variant-numeric:tabular-nums]">
        {money ? (
          <>
            {money.amount} <span className="text-[12px]">{money.currency}</span>
          </>
        ) : (
          "—"
        )}
      </span>
    </div>
  );
}

import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

type Confidence = number | null | undefined;

type Props = {
  label: string;
  /** Pre-rendered value or a raw string/null. Null renders as `—`. */
  value: ReactNode;
  /** 0..1 — when present, shows a colored dot. Skipped when null/undefined. */
  confidence?: Confidence;
  /** Render the value in serif italic accent (used for Mkhedruli party names). */
  geo?: boolean;
  /** Mono font for codes / TINs / dates. */
  mono?: boolean;
  /** Extra emphasis for grand_total etc. */
  emphasis?: boolean;
};

/**
 * One row in a Section: label · value · optional confidence dot.
 * 130px label column, sans/mono value, dot on the right per the App.html
 * design.
 */
export function FieldRow({
  label,
  value,
  confidence,
  geo,
  mono,
  emphasis,
}: Props) {
  const isEmpty =
    value === null ||
    value === undefined ||
    (typeof value === "string" && value.trim() === "");

  return (
    <div
      className={cn(
        "grid grid-cols-[130px_1fr_auto] gap-3.5 items-center px-4 py-2.5 border-b border-line-2 last:border-b-0",
        "hover:bg-paper-2 transition-colors",
      )}
    >
      <span className="font-mono text-[10px] text-ink-3 tracking-[0.07em] uppercase font-medium">
        {label}
      </span>
      <span
        className={cn(
          "min-w-0 break-words",
          isEmpty
            ? "text-ink-4 font-mono text-[13px]"
            : geo
              ? "font-serif italic text-accent text-[15px]"
              : mono
                ? "font-mono text-[13px] text-ink font-medium tracking-[-0.005em]"
                : emphasis
                  ? "font-serif text-[22px] font-medium tracking-[-0.025em] text-ink"
                  : "text-[13px] text-ink",
        )}
      >
        {isEmpty ? "—" : value}
      </span>
      <ConfidenceDot value={confidence} />
    </div>
  );
}

function ConfidenceDot({ value }: { value: Confidence }) {
  if (value === null || value === undefined) {
    return <span className="w-2.5 h-2.5" aria-hidden />;
  }
  const tone =
    value >= 0.8
      ? "bg-accent-2 shadow-[0_0_0_3px_var(--color-accent-soft)]"
      : value >= 0.6
        ? "bg-warn shadow-[0_0_0_3px_var(--color-warn-soft)]"
        : "bg-error shadow-[0_0_0_3px_var(--color-error-soft)]";
  return (
    <span
      title={`${Math.round(value * 100)}%`}
      className={cn("w-2.5 h-2.5 rounded-full", tone)}
    />
  );
}

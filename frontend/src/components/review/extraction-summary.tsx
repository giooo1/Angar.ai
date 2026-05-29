import { cn } from "@/lib/utils";

type Summary = {
  verified: number;
  check: number;
  empty: number;
  present: number;
  total: number;
};

type Props = {
  accepted: boolean;
  summary: Summary;
};

/**
 * Status summary revealed by the file-bar's "History" toggle: a banner with
 * the headline read of the extraction plus a three-count strip
 * (Verified / Needs check / Empty). Counts come from `field_confidence` —
 * model confidence, separate from per-field user confirmations.
 */
export function ExtractionSummary({ accepted, summary }: Props) {
  const { verified, check, empty, present, total } = summary;

  if (total === 0) {
    return (
      <div className="mt-2 bg-paper border border-line rounded-xl px-4 py-3 text-[12.5px] text-ink-3 font-mono">
        No confidence scores for this extraction.
      </div>
    );
  }

  const needsGlance = check > 0;
  const title = needsGlance
    ? `Ready to review — ${check} field${check === 1 ? "" : "s"} need a glance`
    : "Ready to review — everything looks confident";

  return (
    <div className="mt-2 flex flex-col gap-2">
      <div
        className={cn(
          "flex items-start justify-between gap-4 px-4 py-3.5 rounded-xl border",
          needsGlance
            ? "bg-warn-soft border-[rgba(184,136,32,0.28)] text-[#7a5a13]"
            : "bg-accent-soft border-[rgba(45,106,79,0.22)] text-accent",
        )}
      >
        <div className="flex items-start gap-3 min-w-0">
          <span
            className="w-[28px] h-[28px] rounded-full bg-paper border-[1.5px] border-current grid place-items-center flex-none font-bold text-[14px]"
            aria-hidden="true"
          >
            {needsGlance ? "!" : "✓"}
          </span>
          <div className="min-w-0">
            <p className="font-serif text-[15.5px] font-medium tracking-[-0.01em] m-0 leading-tight">
              {title}
            </p>
            <p className="text-[12.5px] m-0 mt-1 leading-relaxed opacity-90">
              {verified} read &amp; confident · {check} need a glance · {empty} not on the document.
              {!accepted && " This document was rejected as not an invoice/waybill."}
            </p>
          </div>
        </div>
        <div className="flex-none text-right">
          <div className="font-mono text-[9.5px] tracking-[0.08em] uppercase opacity-65">
            Confident on
          </div>
          <div className="font-serif text-[22px] font-medium tracking-[-0.015em] leading-none mt-0.5">
            {verified} / {present}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-px bg-line-2 rounded-xl overflow-hidden border border-line-2">
        <Count badge={<span className="text-accent font-bold">✓</span>} badgeBg="bg-accent-soft" label="Verified" value={verified} caption="read & confident" />
        <Count badge={check} badgeBg="bg-warn-soft text-[#7a5a13]" label="Needs check" value={check} caption="read but unsure" />
        <Count badge={empty} badgeBg="bg-neutral-soft text-[#5d626c]" label="Empty" value={empty} caption="not on document" />
      </div>
    </div>
  );
}

function Count({
  badge,
  badgeBg,
  label,
  value,
  caption,
}: {
  badge: React.ReactNode;
  badgeBg: string;
  label: string;
  value: number;
  caption: string;
}) {
  return (
    <div className="bg-paper px-4 py-3 flex items-center gap-3">
      <span
        className={cn(
          "w-[34px] h-[34px] rounded-[9px] flex-none grid place-items-center font-mono font-semibold text-[14px]",
          badgeBg,
        )}
        aria-hidden="true"
      >
        {badge}
      </span>
      <div className="min-w-0">
        <div className="font-mono text-[9.5px] text-ink-3 tracking-[0.07em] uppercase">{label}</div>
        <div className="text-[13px] text-ink font-medium">
          <span className="font-serif text-[18px] font-medium tracking-[-0.015em] mr-1.5">{value}</span>
          {caption}
        </div>
      </div>
    </div>
  );
}

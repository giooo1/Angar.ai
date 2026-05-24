type Props = {
  high: number;
  med: number;
  low: number;
};

/**
 * Three-card horizontal strip under the acceptance banner. Counts the
 * field_confidence dict into high / med / low buckets and visually
 * tells the user where their attention belongs.
 */
export function RiskStrip({ high, med, low }: Props) {
  return (
    <div className="grid grid-cols-3 gap-px bg-line-2 rounded-xl overflow-hidden border border-line-2">
      <Card
        tone="high"
        value={high}
        label="High confidence"
        sub={`${high} field${high === 1 ? "" : "s"} verified`}
      />
      <Card
        tone="med"
        value={med}
        label="Needs review"
        sub={`${med} field${med === 1 ? "" : "s"} under 80%`}
      />
      <Card
        tone="low"
        value={low}
        label="Likely wrong"
        sub={`${low} field${low === 1 ? "" : "s"} under 60%`}
      />
    </div>
  );
}

function Card({
  tone,
  value,
  label,
  sub,
}: {
  tone: "high" | "med" | "low";
  value: number;
  label: string;
  sub: string;
}) {
  const badgeClass =
    tone === "high"
      ? "bg-accent-soft text-accent"
      : tone === "med"
        ? "bg-warn-soft text-[#7a5a13]"
        : "bg-error-soft text-[#7a201d]";

  return (
    <div className="p-3.5 bg-paper flex items-center gap-3">
      <div
        className={`w-9 h-9 rounded-[9px] flex-none grid place-items-center font-mono font-semibold text-[14px] ${badgeClass}`}
      >
        {value}
      </div>
      <div className="flex flex-col gap-[1px] min-w-0">
        <span className="font-mono text-[9.5px] text-ink-3 tracking-[0.07em] uppercase">
          {label}
        </span>
        <span className="text-[12px] text-ink leading-tight tracking-[-0.005em]">
          {sub}
        </span>
      </div>
    </div>
  );
}

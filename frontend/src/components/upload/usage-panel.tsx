type Props = {
  used: number;
  total: number;
  plan: string;
  monthLabel?: string;
  resetsInDays?: number;
};

/**
 * "This month: 47 / 200 extractions" card pinned to the right column.
 *
 * Real usage data lands when the backend exposes a usage endpoint
 * (step 6 work). For now the caller passes hardcoded values.
 */
export function UsagePanel({
  used,
  total,
  plan,
  monthLabel = "Nov 2025",
  resetsInDays = 17,
}: Props) {
  const pct = Math.min(100, Math.round((used / total) * 100));

  return (
    <div className="bg-paper border border-line rounded-xl p-[18px]">
      <h3 className="m-0 mb-3 font-serif text-[17px] font-medium tracking-[-0.015em] flex items-center justify-between">
        This month
        <span className="font-mono text-[11px] text-ink-3 tracking-[0.04em] font-normal normal-case">
          {monthLabel}
        </span>
      </h3>

      <div className="flex items-baseline gap-1.5 mb-3">
        <span className="font-serif text-[38px] tracking-[-0.025em] font-medium text-ink leading-none">
          {used}
        </span>
        <span className="text-sm text-ink-3">/ {total} extractions</span>
      </div>

      <div className="flex justify-between font-mono text-[11px] text-ink-3 tracking-[0.04em] mb-2">
        <span>{pct}% used</span>
        <span>resets in {resetsInDays} days</span>
      </div>

      <div className="h-1.5 bg-line-3 rounded-[3px] overflow-hidden">
        <div
          className="h-full bg-accent rounded-[3px]"
          style={{ width: `${pct}%` }}
        />
      </div>

      <div className="mt-3 flex justify-between items-center text-xs text-ink-3">
        <span>
          {plan} plan · {total}/mo
        </span>
        <a
          href="/settings"
          className="text-accent font-medium no-underline hover:underline"
        >
          Upgrade →
        </a>
      </div>
    </div>
  );
}

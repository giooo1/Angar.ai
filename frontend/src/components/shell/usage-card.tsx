type Props = {
  used: number;
  total: number;
  plan: string;
};

/**
 * Sidebar bottom card: monthly extraction usage + plan badge.
 *
 * Step 6: wired to real org quota; "Upgrade" link is intentionally
 * omitted until there's a real Stripe-backed plan-change UI to link to.
 */
export function UsageCard({ used, total, plan }: Props) {
  const pct = total > 0 ? Math.min(100, Math.round((used / total) * 100)) : 0;

  return (
    <div className="mt-auto p-3 pb-2.5 bg-paper border border-line-2 rounded-lg">
      <div className="font-mono text-[10px] text-ink-3 tracking-[0.06em] uppercase mb-1.5">
        Usage
      </div>
      <div className="font-serif text-[18px] tracking-[-0.015em] text-ink mb-1.5">
        {used} <span className="text-xs text-ink-3">/ {total}</span>
      </div>
      <div className="h-1 bg-line-3 rounded-sm overflow-hidden">
        <div
          className="h-full bg-accent rounded-sm"
          style={{ width: `${pct}%` }}
        />
      </div>
      <div className="mt-2 text-[11px] text-ink-3">{plan} plan</div>
    </div>
  );
}

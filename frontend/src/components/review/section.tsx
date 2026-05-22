import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

type Props = {
  /** Single-character badge in the header (P, D, L, etc.). */
  badge: string;
  title: string;
  count?: string | number;
  className?: string;
  children: ReactNode;
};

/**
 * One card on the right pane of the Review screen.
 * Header: editorial uppercase mono label + accent-colored "ix" badge.
 * Body: the children (typically a list of <FieldRow> or a table).
 */
export function Section({ badge, title, count, className, children }: Props) {
  return (
    <div className={cn("bg-paper border border-line rounded-xl overflow-hidden", className)}>
      <div className="px-4 py-2.5 border-b border-line-2 flex items-center justify-between font-mono text-[10.5px] tracking-[0.07em] uppercase">
        <span className="inline-flex items-center gap-2 text-ink">
          <span className="w-4 h-4 rounded bg-accent-soft text-accent text-[10px] font-semibold inline-grid place-items-center tracking-normal">
            {badge}
          </span>
          {title}
        </span>
        {count !== undefined && <span className="text-ink-3">{count}</span>}
      </div>
      {children}
    </div>
  );
}

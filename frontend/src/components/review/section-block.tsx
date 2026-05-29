import { cn } from "@/lib/utils";

/**
 * Card wrapper used by every right-pane section (Document, Seller,
 * Buyer, Line items, Totals, Flags). Provides the consistent header
 * with optional index letter, title, and a right-side adornment.
 */
export function SectionBlock({
  letter,
  showLetter = false,
  title,
  right,
  children,
  bodyClassName,
}: {
  letter: string;
  /** Render the `letter` as a boxed badge before the title. Off by default —
   *  only the Document section opts in. */
  showLetter?: boolean;
  title: string;
  right?: React.ReactNode;
  children: React.ReactNode;
  bodyClassName?: string;
}) {
  return (
    <div className="bg-paper border border-line rounded-xl overflow-hidden">
      <div className="flex items-center justify-between gap-2.5 px-3.5 py-2 border-b border-line-2">
        <span className="inline-flex items-center gap-2 font-mono text-[10.5px] text-ink-2 tracking-[0.08em] uppercase font-medium">
          {showLetter && (
            <span className="inline-grid place-items-center w-[18px] h-[18px] rounded-[5px] bg-accent-soft text-accent font-sans text-[10px] font-semibold not-italic tracking-normal">
              {letter}
            </span>
          )}
          {title}
        </span>
        {right}
      </div>
      <div className={cn(bodyClassName)}>{children}</div>
    </div>
  );
}

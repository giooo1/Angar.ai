/**
 * Quiet section label for the flat data pane: small uppercase text, no badge,
 * no border, no background. Optional right-aligned adornment (e.g. line count,
 * script indicator).
 */
export function SectionHeader({
  label,
  right,
}: {
  label: string;
  right?: React.ReactNode;
}) {
  return (
    <div className="flex items-center justify-between gap-2.5 mb-2.5">
      <span className="text-[11px] font-medium tracking-[0.08em] uppercase text-ink-3">
        {label}
      </span>
      {right}
    </div>
  );
}

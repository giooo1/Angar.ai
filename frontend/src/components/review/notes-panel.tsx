type Props = {
  notes: string[];
  warnings: string[];
  vatTreatmentReason: string | null;
  rejectionReason: string | null;
};

/**
 * Collapsible "Extraction notes" block. Renders nothing when there's
 * no content. Open by default so users see operator hints without an
 * extra click.
 */
export function NotesPanel({
  notes,
  warnings,
  vatTreatmentReason,
  rejectionReason,
}: Props) {
  const hasContent =
    notes.length > 0 ||
    warnings.length > 0 ||
    !!vatTreatmentReason ||
    !!rejectionReason;
  if (!hasContent) return null;

  return (
    <div className="bg-paper border border-line rounded-xl overflow-hidden">
      <details className="p-4" open>
        <summary className="cursor-pointer outline-none list-none font-mono text-[10.5px] text-ink-3 tracking-[0.08em] uppercase font-medium inline-flex items-center gap-1.5">
          <span className="inline-block transition-transform">▸</span>
          Extraction notes
        </summary>
        <div className="mt-3 flex flex-col gap-3 text-[13px] text-ink-2 leading-[1.65]">
          {rejectionReason && (
            <NoteBlock label="Rejection reason">{rejectionReason}</NoteBlock>
          )}
          {vatTreatmentReason && (
            <NoteBlock label="VAT treatment reason">{vatTreatmentReason}</NoteBlock>
          )}
          {notes.length > 0 && (
            <NoteBlock label="Extraction notes">
              <ul className="m-0 pl-4 list-disc">
                {notes.map((n, i) => (
                  <li key={i} className="mb-1">
                    {n}
                  </li>
                ))}
              </ul>
            </NoteBlock>
          )}
          {warnings.length > 0 && (
            <NoteBlock label="Warnings">
              <ul className="m-0 pl-4 list-disc">
                {warnings.map((w, i) => (
                  <li key={i} className="mb-1 text-warn">
                    {w}
                  </li>
                ))}
              </ul>
            </NoteBlock>
          )}
        </div>
      </details>
    </div>
  );
}

function NoteBlock({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <div className="font-mono text-[10px] text-ink-3 tracking-[0.07em] uppercase mb-1.5 font-medium">
        {label}
      </div>
      <div>{children}</div>
    </div>
  );
}

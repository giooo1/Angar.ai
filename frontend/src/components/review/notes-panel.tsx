import { Section } from "./section";

type Props = {
  notes: string[];
  warnings: string[];
  vatTreatmentReason: string | null;
  rejectionReason: string | null;
};

/**
 * Combined "Notes" section showing every free-text signal the
 * extraction surfaced: extraction_notes, warnings, vat_treatment_reason,
 * rejection_reason. Each rendered under a small heading; the section as
 * a whole hides if nothing is present.
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
    <Section badge="N" title="Notes">
      <div className="px-4 py-3.5 flex flex-col gap-3 text-[12.5px] text-ink-2 leading-[1.55]">
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
    </Section>
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

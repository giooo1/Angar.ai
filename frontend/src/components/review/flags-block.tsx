import { Chip } from "@/components/ui/chip";
import type { CanonicalInvoice } from "@/lib/canonical";
import { SectionBlock } from "./section-block";

type Props = {
  canonical: Pick<
    CanonicalInvoice,
    | "is_vat_invoice"
    | "is_reverse_vat"
    | "is_free_of_charge"
    | "contains_pii_beyond_parties"
    | "document_type"
  >;
};

/**
 * Visual chips summarizing boolean/enum flags from the canonical:
 * document type, VAT mode, free-of-charge, reverse VAT, PII content.
 * Renders the count of detected flags in the section header.
 */
export function FlagsBlock({ canonical }: Props) {
  const flags: Array<{ label: string; variant?: "warn" | "default" | "green" | "error" }> = [];

  if (canonical.is_vat_invoice) flags.push({ label: "VAT invoice", variant: "green" });
  if (canonical.is_reverse_vat) flags.push({ label: "Reverse VAT", variant: "warn" });
  if (canonical.is_free_of_charge)
    flags.push({ label: "Free of charge", variant: "warn" });
  if (canonical.contains_pii_beyond_parties)
    flags.push({ label: "Contains PII", variant: "error" });
  flags.push({ label: canonical.document_type.replace(/_/g, " "), variant: "default" });

  return (
    <SectionBlock
      letter="!"
      title="Flags"
      right={
        <span className="font-mono text-[10.5px] text-ink-3 tracking-[0.04em]">
          {flags.length} detected
        </span>
      }
    >
      <div className="px-4 py-3.5 flex flex-wrap gap-2">
        {flags.map((f, i) => (
          <Chip key={i} variant={f.variant ?? "default"}>
            {f.label}
          </Chip>
        ))}
      </div>
    </SectionBlock>
  );
}
